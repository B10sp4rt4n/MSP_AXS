export const PORTAL_ROLES = {
  guardia: ["GUARDIA", "MSP_ADMIN", "ADMIN_CONDOMINIO"],
  residente: ["RESIDENTE", "MSP_ADMIN", "ADMIN_CONDOMINIO"],
  admin: ["ADMIN_CONDOMINIO", "MSP_ADMIN"],
  msp: ["MSP_ADMIN"],
} as const;
