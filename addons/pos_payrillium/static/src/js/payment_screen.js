/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";

import { PayrilliumAPI } from "@pos_payrillium/js/api_service";
import { ConfigLoader } from "@pos_payrillium/js/config_loader";

console.log("🔥 POS Payrillium - Payment Screen LOADING (Odoo 17)");

patch(PaymentScreen.prototype, {
  async setup(...args) {
    await super.setup?.();
    this.payrilliumAPI = PayrilliumAPI;
    this.rpc = this.env.services.rpc;
    this.popup = this.env.services.popup;
    // this.pos = this.env.services.pos;
    this._posService = this.env.services.pos;
    console.log("🚀 Initializando pantalla de pago Payrillium (Odoo 17)");
    try {
      const config = await this._loadConfiguration();
      console.log("⚙️ Configuración de pantalla de pago cargada:", config);
      this._initializePaymentMethod(config);
    } catch (error) {
      console.error("⚠️ Error de configuración:", error);
      this._showConfigurationError();
    }
  },

  async _loadConfiguration() {
    try {
      const rpc = this.rpc || this.env.services.rpc;
      const fullData = await ConfigLoader.getFullPaymentMethodData(rpc);
      this.paymentMethodName = await ConfigLoader.getPaymentMethodName(rpc);
      this.paymentMethodColor = await ConfigLoader.getPaymentMethodColor(rpc);
      this.paymentMethodIcon = await ConfigLoader.getPaymentMethodIcon(rpc);
      this.receivableAccountId = fullData.receivable_account_id;
      this.paymentProviderId = fullData.payment_provider_id;
      this.terminalId = fullData.terminal_id;
      this._applyPayrilliumStyles();
      console.log("✅ Configuración cargada:", {
        name: this.paymentMethodName,
        color: this.paymentMethodColor,
        icon: this.paymentMethodIcon,
        paymentProviderId: this.paymentProviderId,
      });
      return {
        name: this.paymentMethodName,
        color: this.paymentMethodColor,
        icon: this.paymentMethodIcon,
      };
    } catch (error) {
      console.error("❌ Error cargando configuración:", error);
    }
  },

  _initializePaymentMethod(config) {
    console.log("🔧 Configurando método de pago con:", config);
    this.payrilliumAPI = PayrilliumAPI;
  },

  _showConfigurationError() {
    this.popup.add("ErrorPopup", {
      title: "Error de configuración",
      body: "No se pudo inicializar la configuración de pago. Revisa tus ajustes.",
    });
  },

  _applyPayrilliumStyles() {
    console.log("🎨 Aplicando estilos Payrillium...");
    const buttons = [
      ...document.querySelectorAll(".paymentmethod .payment-name"),
    ];
    for (const el of buttons) {
      if (el.textContent.trim().toLowerCase() === this.paymentMethodName) {
        const button = el.closest(".paymentmethod");
        button.style.display = "flex";
        button.style.alignItems = "center";
        button.style.justifyContent = "flex-start";
        button.style.gap = "10px";
        button.style.padding = "10px 16px";
        button.style.borderRadius = "12px";
        button.style.backgroundColor = this.paymentMethodColor || "#003366";
        button.style.color = "white";
        button.style.fontWeight = "bold";
        if (!button.querySelector("img")) {
          const icon = document.createElement("img");
          icon.src =
            this.paymentMethodIcon ||
            "/pos_payrillium/static/description/icon.png";
          icon.alt = "Payrillium";
          icon.style.height = "24px";
          icon.style.width = "24px";
          icon.style.objectFit = "contain";
          icon.style.marginRight = "4px";
          icon.style.flexShrink = "0";
          icon.style.verticalAlign = "middle";
          button.insertBefore(icon, button.firstChild);
        }
      }
    }
  },

  async _createPayrilliumTransaction(params) {
    try {
      await this.rpc("/web/dataset/call_kw", {
        model: "payment.transaction",
        method: "create_from_pos_payrillium",
        args: [params],
        kwargs: {},
      });
      console.log("✅ payment.transaction creado para Payrillium:", params);
    } catch (error) {
      console.error("❌ Error creando payment.transaction:", error);
    }
  },

  generateExecutionId() {
    return Math.random().toString(36).substring(2, 10) + Date.now();
  },

  async _processPayrilliumPayment(paymentLine) {
    try {
      this.executionId = this.generateExecutionId();
      console.log(paymentLine, "paymentLine");

      console.log("🧩 Nuevo Execution ID:", this.executionId);
      const showResult = await this.payrilliumAPI.showBasket(
        this.rpc,
        paymentLine,
        this.executionId
      );
      if (!showResult.success) {
        throw new Error("Error mostrando monto en el terminal");
      }
      await new Promise((resolve) => setTimeout(resolve, 2000));
      const cardTypeResponse = await this.payrilliumAPI.requestCardType(
        this.rpc,
        this.executionId
      );
      const cardType = cardTypeResponse.data?.data?.selection?.toUpperCase();
      console.log("💳 Tipo de tarjeta seleccionada:", cardType);
      if (
        !cardTypeResponse.success ||
        cardTypeResponse.data?.success === "CANCELLED"
      ) {
        throw new Error("Selección de tarjeta cancelada en el terminal");
      }
      let tipAmount = 0;
      if (this._posService.config.iface_tipproduct) {
        tipAmount = await this.payrilliumAPI.showTipSelection(
          this.rpc,
          paymentLine,
          this.executionId
        );
      }
      console.log("💰 Montos iniciales:", {
        total: paymentLine.order.get_total_with_tax(),
        due: paymentLine.order.get_due(),
        payment_line: paymentLine.amount,
      });
      if (tipAmount > 0) {
        console.log("🎯 Agregando propina:", tipAmount);
        paymentLine.order.set_tip(tipAmount);
        console.log("💵 Montos después de set_tip:", {
          new_total: paymentLine.order.get_total_with_tax(),
          current_due: paymentLine.order.get_due(),
        });
        const new_total = paymentLine.order.get_total_with_tax();
        paymentLine.set_amount(new_total);
        console.log("✅ Estado final tras propina:", {
          order_total: new_total,
          line_amount: paymentLine.amount,
          final_due: paymentLine.order.get_due(),
        });
      }
      const paymentRef = `POS-${this._posService.config.name}-${paymentLine.order.uid}-${paymentLine.cid}`;
      const paymentResult = await this.payrilliumAPI.capturePayment(
        this.rpc,
        paymentLine,
        cardType,
        tipAmount,
        paymentRef,
        this.executionId
      );
      const isSuccessAuth =
        paymentResult.success === true &&
        paymentResult.data?.state === "SUCCESS_AUTH";
      if (!isSuccessAuth) {
        if (cardType === "CREDIT") {
          console.warn(
            "🔄 Falló la captura con tarjeta de CRÉDITO, enviando authReversal..."
          );
          await this.payrilliumAPI.authReversal(this.rpc, {
            payment_id: `${paymentRef}r`,
            transaction_id: paymentResult.data?.data?.message?.transactionId,
            totalAmount: paymentLine.order.get_total_with_tax().toFixed(2),
            reason: "",
            executionId: this.executionId,
          });
        }
        paymentLine.set_payment_status("retry");
        console.log(paymentResult, "paymentResult");
        throw new Error(
          paymentResult.data?.data?.message?.error || "Pago no aprobado"
        );
      }
      const transactionId = paymentResult.data?.data?.message?.transactionId;
      if (cardType === "CREDIT") {
        const capturePayload = {
          payment_id: `${paymentRef}c`,
          amount: paymentLine.order.get_total_with_tax().toFixed(2),
          transaction_id: transactionId,
          executionId: this.executionId,
        };
        console.log(
          "💳 Tarjeta CRÉDITO detectada - enviando /payment/capture:",
          capturePayload
        );
        const captureResult = await this.payrilliumAPI.captureCreditPayment(
          this.rpc,
          capturePayload,
          this.executionId
        );
        const isSuccessCapture =
          captureResult.success === true &&
          captureResult.data?.state === "SUCCESS_CAPTURE";
        if (!isSuccessCapture) {
          paymentLine.set_payment_status("retry");
          throw new Error(
            captureResult.data?.data?.message?.error || "Fallo en la captura"
          );
        }
        const captureStatus = captureResult.data?.data?.message?.status;
        const reconciliationId =
          captureResult.data?.data?.message?.reconciliationId;
        const captureId = captureResult.data?.data?.message?.id;
        console.log("✅ Captura exitosa:", {
          status: captureStatus,
          reconciliationId,
          captureId,
        });
      }
      paymentLine.set_payment_status("done");
      paymentLine.transaction_id = transactionId;
      paymentLine.provider_id = this.paymentProviderId;

      await this._createPayrilliumTransaction({
        reference: paymentRef,
        provider_id: this.paymentProviderId,
        payment_method_id: paymentLine.payment_method.id,
        acquirer_reference: transactionId,
        amount: parseFloat(paymentLine.order.get_total_with_tax().toFixed(2)),
        order_uid: paymentLine.order.uid,
        card_type: cardType,
        terminal_id: Array.isArray(
          this._posService.config.payrillium_terminal_id
        )
          ? this._posService.config.payrillium_terminal_id[0]
          : this._posService.config.payrillium_terminal_id,
      });
      console.log("Due:", paymentLine.order.get_due(), "resto");
      return true;
    } catch (error) {
      paymentLine.set_payment_status("retry");
      throw error;
    }
  },

  async _finalizeRefundTransaction({
    paymentLine,
    cardType,
    transaction_id,
    payment_id,
    amount,
  }) {
    paymentLine.transaction_id = transaction_id;
    paymentLine.set_payment_status("done");
    paymentLine.provider_id = this.paymentProviderId || "";

    await this._createPayrilliumTransaction({
      reference: payment_id,
      provider_id: this.paymentProviderId,
      payment_method_id: paymentLine.payment_method.id,
      acquirer_reference: transaction_id,
      amount: parseFloat(amount),
      order_pos_reference: paymentLine.order.uid,
      card_type: cardType,
      terminal_id: Array.isArray(this._posService.config.payrillium_terminal_id)
        ? this._posService.config.payrillium_terminal_id[0]
        : this._posService.config.payrillium_terminal_id,
    });
  },

  async _isPayrilliumPayment(paymentLine) {
    return (
      this.paymentMethodName &&
      paymentLine.payment_method.name?.toLowerCase() === this.paymentMethodName
    );
  },

  async validateOrder(force_validation) {
    this.executionId = this.generateExecutionId();
    console.log(this.paymentLines, "paymentLines");
    console.log(this.currentOrder, "currentOrder");
    const total = this.currentOrder.get_total_with_tax();
    const lines = this.paymentLines;
    const isRefund = total < 0;
    console.log(total, "total");
    console.log(isRefund, "isRefund");
    console.log(lines, "lines");

    const hasPayrilliumPayment = await Promise.any(
      lines.map((line) => this._isPayrilliumPayment(line))
    );

    if (hasPayrilliumPayment) {
      for (const line of lines) {
        console.log(line, "line");
        if (!(await this._isPayrilliumPayment(line))) continue;
        if (isRefund) {
          try {
            const refundedLine = this.currentOrder
              .get_orderlines()
              .find((ol) => Boolean(ol.refunded_orderline_id));
            if (!refundedLine)
              throw new Error("No se encontró producto a reembolsar.");
            console.log(refundedLine, "refundedLine");
            const refundedLineId = refundedLine.refunded_orderline_id;
            console.log(refundedLineId, "refundedLineId");
            const [refundedLineBackend] = await this.rpc(
              "/web/dataset/call_kw",
              {
                model: "pos.order.line",
                method: "read",
                args: [[refundedLineId], ["order_id"]],
                kwargs: {},
              }
            );
            console.log("🧾 Resultado de línea:", refundedLineBackend);
            const order_id = refundedLineBackend?.order_id?.[0];
            if (!order_id) throw new Error("❌ order_id no encontrado");
            console.log("✅ order_id extraído:", order_id);
            const payments = await this.rpc("/web/dataset/call_kw", {
              model: "pos.payment",
              method: "search_read",
              args: [[["pos_order_id", "=", order_id]], ["transaction_id"]],
              kwargs: {},
            });
            console.log("💸 Pagos encontrados:", payments);
            const transaction_id = payments?.[0]?.transaction_id;
            if (!transaction_id)
              throw new Error("❌ transaction_id no encontrado");
            console.log("📌 transaction_id final:", transaction_id);
            if (!transaction_id)
              throw new Error(
                "No se encontró transaction ID para la orden original"
              );
            const [trx] = await this.rpc("/web/dataset/call_kw", {
              model: "payment.transaction",
              method: "search_read",
              args: [
                [["provider_reference", "=", transaction_id]],
                [
                  "card_type",
                  "provider_reference",
                  "reference",
                  "payrillium_terminal_id",
                ],
              ],
              kwargs: {},
            });
            console.log(trx, "trx");
            const cardType = trx.card_type;
            const terminalId = trx.payrillium_terminal_id;
            const paymentId = trx.reference;
            const amount = Math.abs(total).toFixed(2);
            let result;

            if (cardType === "CREDIT") {
              result = await this.payrilliumAPI.refundCredit(this.rpc, {
                payment_id: `${paymentId}r`,
                transaction_id: transaction_id,
                totalAmount: amount,
                terminal_id: terminalId,
              });
            } else {
              result = await this.payrilliumAPI.refundDebit(
                this.rpc,
                {
                  payment_id: `${paymentId}r`,
                  transaction_id: transaction_id,
                  totalAmount: amount,
                  tips: "",
                  cashback: "",
                },
                this.executionId
              );
            }
            if (!result.success) {
              throw new Error(result.message || "Reembolso fallido.");
            }
            await this._finalizeRefundTransaction({
              paymentLine: line,
              cardType,
              transaction_id,
              payment_id: `${paymentId}r`,
              amount,
            });
          } catch (error) {
            this.popup.add("ErrorPopup", {
              title: "Error de reembolso",
              body: error.message,
            });
            return false;
          }
        } else {
          try {
            await this._processPayrilliumPayment(line);
          } catch (error) {
            this.popup.add("ErrorPopup", {
              title: "Error de pago",
              body: error.message,
            });
            return false;
          }
        }
      }
    }
    return super.validateOrder(force_validation);
  },

  async validatePaymentLine(paymentLine) {
    console.log("🔄 validatePaymentLine", paymentLine);
    // Puedes adaptar lógica aquí si necesitas validación especial para Payrillium
    return super.validatePaymentLine?.(paymentLine);
  },

  async _finalizeValidation() {
    const payrilliumLines = this.paymentLines.filter(
      (line) =>
        line.payment_method.name?.toLowerCase() === this.paymentMethodName
    );
    for (const line of payrilliumLines) {
      if (!line.transaction_id) {
        const message = `Payrillium payment without transaction ID: ${line.cid}`;
        console.error(message);
        throw new Error(message);
      }
    }
    const button = document.querySelector(".paymentmethods .selected-button");
    if (button && !button.classList.contains("payrillium-button")) {
      button.classList.add("payrillium-button");
      const icon = document.createElement("img");
      icon.src = "/pos_payrillium/static/description/icon.png";
      button.prepend(icon);
    }
    return super._finalizeValidation();
  },

  async cancelPayment(paymentLine) {
    if (
      paymentLine.payment_method.name?.toLowerCase() ===
        this.paymentMethodName &&
      paymentLine.transaction_id
    ) {
      try {
        await this.payrilliumAPI.voidCapture(
          this.rpc,
          paymentLine.transaction_id
        );
        paymentLine.set_payment_status("retry");
        return true;
      } catch (error) {
        this.popup.add("ErrorPopup", {
          title: "Error al cancelar",
          body: "No se pudo cancelar el pago en el terminal",
        });
        return false;
      }
    }
    return super.cancelPayment(paymentLine);
  },

  async _sendPaymentRequest(lineOrEvent) {
    console.log("🔥 _sendPaymentRequest llamado!", lineOrEvent);
    const paymentLine = lineOrEvent?.detail ?? lineOrEvent;
    const methodName = paymentLine.payment_method?.name?.toLowerCase();
    if (!this.paymentMethodName || methodName !== this.paymentMethodName) {
      return super._sendPaymentRequest(paymentLine);
    }
    const order = this.currentOrder;
    order.select_paymentline(paymentLine);
    try {
      await this._processPayrilliumPayment(paymentLine);
      if (
        order.is_paid() &&
        this._posService &&
        this._posService.currency &&
        Math.abs(order.get_due()) < (this._posService.currency.rounding || 0.01)
      ) {
        console.log(
          "✅ Orden pagada tras reintento. Finalizando con super.validateOrder..."
        );
        await super.validateOrder();
      } else {
        console.warn(
          "⚠️ Orden no pagada completamente aún. Esperando más acciones."
        );
      }
      return true;
    } catch (error) {
      this.popup.add("ErrorPopup", {
        title: "Error al reintentar pago",
        body: error.message || "No se pudo reintentar el pago",
      });
      return false;
    }
  },

  _handlePaymentError(error) {
    console.error("Detalles del error de pago:", error);
    this.popup.add("ErrorPopup", {
      title: "Error de pago",
      body: error.message || "Ocurrió un error procesando el pago",
    });
  },
});

console.log("✅ POS Payrillium - Payment Screen READY (Odoo 17)");
