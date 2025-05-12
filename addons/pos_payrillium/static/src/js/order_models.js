/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { Order } from "@point_of_sale/app/store/models";
import { PayrilliumAPI } from "@pos_payrillium/js/api_service";

patch(Order.prototype, {
  async add_product(product, options) {
    // Llama al método original
    const result = await super.add_product(product, options);

    // Sincroniza con el terminal SOLO si la orden está activa (no borrada, no pagada, etc.)
    try {
      // El contexto de "this" es la orden
      const pos = this.pos;
      const rpc = pos.env.services.rpc;
      await PayrilliumAPI.showBasket(rpc, this);
      console.log("✅ Terminal sincronizado tras agregar producto");
    } catch (error) {
      console.error("❌ Error sincronizando con terminal:", error);
    }

    return result;
  },
});
