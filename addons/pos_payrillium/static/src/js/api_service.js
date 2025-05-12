/** @odoo-module **/

import { ConfigLoader } from "@pos_payrillium/js/config_loader";
console.log("🔥 POS Payrillium - API Service LOADING");

export const PayrilliumAPI = {
  async showBasket(rpc, input, executionId = null) {
    console.log("🚀 Starting showBasket request");

    const order = input?.order || input;

    if (!order || typeof order.get_orderlines !== "function") {
      console.error(
        "❌ Invalid input: expected order or paymentLine with order"
      );
      return { success: false, message: "Invalid order input" };
    }

    const lines = order.get_orderlines();
    const imageBaseUrl = await ConfigLoader.getImageBaseUrl(rpc);

    const products = lines.map((line) => ({
      id: line.product.id,
      sale_upc_code: line.product.barcode || "N/A",
      upc_code: line.product.barcode || "N/A",
      image: `${imageBaseUrl}/image/${line.product.id}` || "",
      name: line.product.display_name,
      qty: `${line.quantity}`,
      price: `${line.get_unit_price().toFixed(2)}`,
      total: `${line.get_display_price().toFixed(2)}`,
      group_name: "DEFAULT",
    }));

    const discount = lines.reduce((acc, line) => {
      const line_total = line.get_unit_price() * line.quantity;
      return acc + (line_total * line.get_discount()) / 100;
    }, 0);

    const payload = {
      products,
      currency: "USD",
      subtotal: order.get_total_without_tax().toFixed(2),
      tax: order.get_total_tax().toFixed(2),
      discount: discount.toFixed(2),
      items: `${lines.length}`,
      total: order.get_total_with_tax().toFixed(2),
      cash_discount: "0.00",
      non_cash_adjustment: "0.00",
      total_after_cash_discount: order.get_total_with_tax().toFixed(2),
      cash_discount_config_active: true,
      transaction_type: "sale",
    };

    try {
      const response = await rpc("/payrillium/proxy/basket", {
        kwargs: { ...payload, executionId },
      });
      return response;
    } catch (error) {
      console.error("❌ Error during showBasket request:", error);
      return { status: "error", message: error.message };
    }
  },

  async requestCardType(rpc, executionId = null) {
    try {
      const response = await rpc("/payrillium/proxy/card", {
        kwargs: { data: "", executionId },
      });
      return response;
    } catch (error) {
      console.error("❌ Error during requestCardType:", error);
      return { success: false, message: error.message };
    }
  },

  async showTipSelection(rpc, paymentLine, executionId = null) {
    const amount = paymentLine.order.get_total_with_tax();
    const tipOptions = ["1", "2", "5", "Custom", "No Tip"];
    let tipAmount = 0;

    try {
      const payload = {
        title: "Select Tip",
        menu: tipOptions,
        amount,
      };
      const tipResult = await rpc("/payrillium/proxy/tip", {
        kwargs: { ...payload, executionId },
      });

      const resultType = tipResult?.data?.type;
      const resultData = tipResult?.data?.data;

      if (resultType?.includes("TipResultCustom")) {
        tipAmount = parseFloat(resultData?.value || 0);
      } else if (resultType?.includes("TipResultOption")) {
        const index = resultData?.selection;
        const option = tipOptions[index];
        const parsed = parseFloat(option);
        if (!isNaN(parsed)) tipAmount = parsed;
      }
    } catch (error) {
      console.error("❌ Error during tip selection:", error);
    }

    return tipAmount;
  },

  async capturePayment(
    rpc,
    paymentLine,
    cardType,
    tipAmount,
    paymentRef,
    executionId = null
  ) {
    const payload = {
      cardType: cardType || "DEBIT",
      payment_id: paymentRef,
      amount: paymentLine.order.get_total_with_tax().toFixed(2),
      tip: tipAmount ? tipAmount.toFixed(2) : "",
    };

    try {
      const response = await rpc("/payrillium/payment/auth", {
        kwargs: { ...payload, executionId },
      });
      return response;
    } catch (error) {
      console.error("❌ Error during capturePayment:", error);
      return { status: "error", message: error.message };
    }
  },

  async captureCreditPayment(rpc, payload, executionId = null) {
    try {
      const response = await rpc("/payrillium/payment/capture", {
        kwargs: { ...payload, executionId },
      });
      return response;
    } catch (error) {
      console.error("❌ Error during captureCreditPayment:", error);
      return { success: false, message: error.message };
    }
  },

  async authReversal(rpc, payload, executionId = null) {
    try {
      const response = await rpc("/payrillium/payment/auth_reversal", {
        kwargs: { ...payload, executionId },
      });
      return response;
    } catch (error) {
      console.error("❌ Error during authReversal:", error);
      return { success: false, message: error.message };
    }
  },

  async refundDebit(rpc, payload, executionId = null) {
    try {
      const response = await rpc("/payrillium/payment/refund_debit", {
        kwargs: { ...payload, executionId },
      });
      return response;
    } catch (error) {
      console.error("❌ Error during refundDebit:", error);
      return { success: false, message: error.message };
    }
  },

  async refundCredit(rpc, payload, executionId = null) {
    try {
      const response = await rpc("/payrillium/payment/refund", {
        kwargs: { ...payload, executionId },
      });
      return response;
    } catch (error) {
      console.error("❌ Error during refundCredit:", error);
      return { success: false, message: error.message };
    }
  },

  async send_payment_request(cid, amount, executionId = null) {
    try {
      const response = await this.showBasket(rpc, amount, executionId);
      if (response.status === "error") throw new Error(response.message);

      return {
        cid,
        payment_status: response.status === "success" ? "done" : "retry",
        transaction_id: response.transaction_id || null,
        message: response.message,
      };
    } catch (error) {
      console.error("❌ Error in send_payment_request:", error);
      return {
        cid,
        payment_status: "retry",
        message: error.message,
      };
    }
  },
};

console.log("✅ POS Payrillium - API Service READY");
