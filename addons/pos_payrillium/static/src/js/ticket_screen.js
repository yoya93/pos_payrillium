/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";

console.log("📦 Patching TicketScreen...");

patch(TicketScreen.prototype, {
  async onCreateNewOrder() {
    console.log("🖱️ Custom onCreateNewOrder from patch");
    await super.onCreateNewOrder();
  },
});

console.log("✅ Patch applied to TicketScreen");
