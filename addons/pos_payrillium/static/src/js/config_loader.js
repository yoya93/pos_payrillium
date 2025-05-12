/** @odoo-module **/

export const ConfigLoader = {
  async getPaymentMethodName(rpc) {
    try {
      const result = await rpc("/payrillium/payment_method_name", {
        params: {},
      });
      return result.payment_method_name?.toLowerCase() || null;
    } catch (error) {
      console.error("❌ Error loading payment method name:", error);
      return null;
    }
  },

  async getPaymentMethodColor(rpc) {
    try {
      const result = await rpc("/payrillium/payment_method_color", {
        params: {},
      });
      return result.color || "#003366";
    } catch (error) {
      console.error("❌ Error loading payment method color:", error);
      return "#003366";
    }
  },

  async getPaymentMethodIcon(rpc) {
    try {
      const result = await rpc("/payrillium/payment_method_icon", {
        params: {},
      });
      return result.icon || "/pos_payrillium/static/description/icon.png";
    } catch (error) {
      console.error("❌ Error loading payment method icon:", error);
      return "/pos_payrillium/static/description/icon.png";
    }
  },

  async getImageBaseUrl(rpc) {
    try {
      const result = await rpc("/payrillium/image_base_url", { params: {} });
      return result.image_base_url || "http://localhost:8069";
    } catch (error) {
      console.error("❌ Error loading image base URL:", error);
      return "http://localhost:8069";
    }
  },

  async getFullPaymentMethodData(rpc) {
    try {
      const result = await rpc("/payrillium/payment_method_data", {
        params: {},
      });
      console.log(result, "result");

      return result || {};
    } catch (error) {
      console.error("❌ Error loading full payment method data:", error);
      return {};
    }
  },
};
