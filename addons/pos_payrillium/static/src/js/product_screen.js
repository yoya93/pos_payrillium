/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { PayrilliumAPI } from "@pos_payrillium/js/api_service";

console.log("🟢 Patch product_screen.js");

patch(ProductScreen.prototype, {
  // async clickProduct(event) {
  //   await super.clickProduct(event);
  //   console.log("🛒 Product added:", event.detail.display_name);
  //   await this._syncBasketWithTerminal();
  // },
  async updateSelectedOrderline(event) {
    await super.updateSelectedOrderline(event);
    console.log("🔄 Order line updated", {
      orderline: this.currentOrder.get_selected_orderline(),
      timestamp: new Date().toISOString(),
    });
    await this._syncBasketWithTerminal();
  },
  // async onClickPay() {
  //   console.log("💰 Payment button clicked", {
  //     total: this.currentOrder,
  //     products: this.currentOrder.get_orderlines().length,
  //     timestamp: new Date().toISOString(),
  //   });

  //   const isRefund = this.currentOrder.is_return;
  //   console.log(this.currentOrder);
  //   console.log(isRefund);

  //   await this._syncBasketWithTerminal();
  //   await super.onClickPay();
  // },

  // async _barcodeProductAction(code) {
  //   await super._barcodeProductAction(code);
  //   this.currentOrder._updateRewards();
  //   await this._syncBasketWithTerminal?.();
  // },
  // async _barcodeGS1Action(code) {
  //   await super._barcodeGS1Action(code);
  //   this.currentOrder._updateRewards();
  //   await this._syncBasketWithTerminal?.();
  // },

  // async _showDecreaseQuantityPopup() {
  //   const result = await super._showDecreaseQuantityPopup();
  //   if (result) {
  //     this.currentOrder._updateRewards();
  //     await this._syncBasketWithTerminal?.();
  //   }
  // },

  async _syncBasketWithTerminal() {
    const order = this.currentOrder;
    const rpc = this.env.services.rpc;
    try {
      console.log("🔄 Synchronizing basket with terminal...");
      await PayrilliumAPI.showBasket(rpc, order);
      console.log("✅ Terminal updated with current products");
    } catch (error) {
      console.error("❌ Error synchronizing with terminal:", error);
    }
  },
});
