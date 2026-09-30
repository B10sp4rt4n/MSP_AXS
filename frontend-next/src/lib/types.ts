export interface Visita {
  visita_id: string;
  condominio_id: string;
  nombre_visitante: string;
  casa_unidad: string;
  destino_id?: string | null;
  destino_tipo?: string | null;
  destino_motivo?: string | null;
  tipo_visita: string;
  estado: string; // pendiente | activa | completada | cancelada
  qr_token: string | null;
  entrada_registrada_en: string | null;
  salida_registrada_en: string | null;
  created_at: string;
}

export interface Condominio {
  condominio_id: string;
  nombre: string;
}

export interface NuevaVisitaPayload {
  nombre_visitante: string;
  casa_unidad: string;
  tipo_visita: string;
  placa?: string;
  condominio_id: string;
}

export interface ResidenteCasa {
  usuario_id: string;
  nombre: string;
  email: string;
  rol: string;
}

export interface CasaItem {
  casa_id: string;
  numero: string;
  tipo: string;
  descripcion?: string;
  residente: ResidenteCasa | null;
}

export interface CasasResponse {
  condominio_id: string;
  total_casas: number;
  casas: CasaItem[];
}
