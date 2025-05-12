/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";

console.log("🟢 Patch pos_store.js");

patch(PosStore.prototype, {
  async _processData(loadedData) {
    await super._processData(loadedData);

    const paymentMethods = loadedData["pos_payment_method"];
    console.log(paymentMethods, "📦 loadedData pos_payment_method");

    if (!paymentMethods || !Array.isArray(paymentMethods)) {
      console.warn("⚠️ No pos_payment_method in loadedData");
      return;
    }

    for (const method of paymentMethods) {
      const existing = this.payment_methods.find((pm) => pm.id === method.id);
      if (existing) {
        existing.payment_provider_id = method.payment_provider_id;
      }
    }
  },
});
