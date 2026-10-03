export interface User {
  id: string;
  full_name: string;
  phone: string | null;
  role: "customer" | "staff" | "owner" | "admin";
}

export interface ParkingLot {
  id: string;
  owner_id: string;
  name: string;
  address: string;
  city: string;
  latitude: number;
  longitude: number;
  description: string | null;
  status: string;
  parking_type: string;
  parking_mode: string;
  identification_method: string;
  is_closed: boolean;
  closure_message: string | null;
  available_slots: number;
  starting_hourly_rate: number | null;
}

export interface ParkingSlot {
  id: string;
  parking_lot_id: string;
  slot_number: string;
  hourly_rate: number;
  status: "available" | "occupied" | "maintenance";
  category: string;
  level_name: string | null;
  zone_name: string | null;
}

export interface Booking {
  id: string;
  customer_id: string;
  parking_slot_id: string;
  starts_at: string;
  ends_at: string;
  total_amount: number;
  status: "pending" | "confirmed" | "cancelled" | "completed";
}

export interface Vehicle {
  id: string;
  user_id: string;
  plate_number: string;
  label: string;
  vehicle_type: string;
  is_default: boolean;
}

export interface ParkingSession {
  id: string;
  public_id: string;
  parking_lot_id: string;
  parking_slot_id: string | null;
  vehicle_id: string;
  customer_id: string;
  status: "active" | "closed";
  entry_method: string;
  entry_at: string;
  exit_at: string | null;
  synced_at: string | null;
  valet_status: string;
  valet_handover_at: string | null;
  valet_retrieval_requested_at: string | null;
  valet_retrieved_at: string | null;
  emergency_priority: boolean;
  slot_override: boolean;
  override_reason: string | null;
}

export interface CorporatePass {
  id: string;
  pass_code: string;
  parking_lot_id: string;
  holder_user_id: string | null;
  vehicle_id: string | null;
  pass_type: string;
  visitor_name: string | null;
  visitor_phone: string | null;
  starts_at: string;
  expires_at: string | null;
  status: string;
}

const defaultApiUrl = process.env.NODE_ENV === "production" ? "/api/v1" : "http://localhost:8000/api/v1";
const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? defaultApiUrl).replace(/\/$/, "");

export class ApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
    this.name = "ApiError";
  }
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  if (typeof window !== "undefined") {
    const token = window.localStorage.getItem("parken_access_token");
    if (token) headers.set("Authorization", `Bearer ${token}`);
  }
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, { ...options, headers });
  } catch (error) {
    if (error instanceof TypeError) {
      throw new ApiError(
        `Cannot reach the ORT API at ${API_URL}. Start the API and database, then try again.`,
        0,
      );
    }
    throw error;
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null) as { detail?: string } | null;
    throw new ApiError(body?.detail ?? `ORT service returned ${response.status}`, response.status);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const parkEnApi = {
  search: (params: URLSearchParams, signal?: AbortSignal) =>
    api<ParkingLot[]>(`/parking/search?${params.toString()}`, { signal }),
  requestOtp: (phone: string, fullName?: string) =>
    api<{ expires_in: number; dev_code?: string }>("/auth/otp/request", {
      method: "POST",
      body: JSON.stringify({ phone, ...(fullName ? { full_name: fullName } : {}) }),
    }),
  verifyOtp: (phone: string, code: string) =>
    api<{ access_token: string; expires_in: number }>("/auth/otp/verify", {
      method: "POST",
      body: JSON.stringify({ phone, code }),
    }),
  me: () => api<User>("/auth/me"),
  slots: (lotId: string) => api<ParkingSlot[]>(`/parking-slots?parking_lot_id=${lotId}`),
  bookings: () => api<Booking[]>("/bookings"),
  createBooking: (body: {
    customer_id: string;
    parking_slot_id: string;
    starts_at: string;
    ends_at: string;
    total_amount: number;
    status: "pending";
  }) => api<Booking>("/bookings", { method: "POST", body: JSON.stringify(body) }),
  updateBooking: (id: string, status: Booking["status"]) =>
    api<Booking>(`/bookings/${id}`, { method: "PATCH", body: JSON.stringify({ status }) }),
  vehicles: () => api<Vehicle[]>("/vehicles"),
  createVehicle: (body: {
    plate_number: string;
    label: string;
    vehicle_type: string;
    is_default: boolean;
  }) => api<Vehicle>("/vehicles", { method: "POST", body: JSON.stringify(body) }),
  deleteVehicle: (id: string) => api<void>(`/vehicles/${id}`, { method: "DELETE" }),
  sessions: () => api<ParkingSession[]>("/parking-sessions"),
  lookupSession: (parkingLotId: string, method: string, value: string) =>
    api<ParkingSession>(`/parking-sessions/lookup?parking_lot_id=${encodeURIComponent(parkingLotId)}&method=${method}&value=${encodeURIComponent(value)}`),
  assignSessionSlot: (sessionId: string, slotId: string, overrideReason?: string) =>
    api<ParkingSession>(`/parking-sessions/${sessionId}/assign`, {
      method: "POST",
      body: JSON.stringify({ parking_slot_id: slotId, override_reason: overrideReason || null }),
    }),
  createSession: (body: {
    parking_lot_id: string;
    vehicle_id: string;
    parking_slot_id: string;
    entry_method: "walk_in";
  }) =>
    api<ParkingSession & { qr_token: string }>("/parking-sessions", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  closeSession: (id: string) =>
    api<ParkingSession>(`/parking-sessions/${id}/close`, { method: "POST" }),
  requestValetRetrieval: (id: string) =>
    api<ParkingSession>(`/parking-sessions/${id}/valet/retrieval`, { method: "POST" }),
  completeValetRetrieval: (id: string) =>
    api<ParkingSession>(`/parking-sessions/${id}/valet/complete-retrieval`, { method: "POST" }),
  recordValetHandover: (id: string) =>
    api<ParkingSession>(`/parking-sessions/${id}/valet/handover`, { method: "POST" }),
  setEmergencyPriority: (id: string, emergencyPriority: boolean, overrideReason: string | null) =>
    api<ParkingSession>(`/parking-sessions/${id}/priority`, {
      method: "PATCH",
      body: JSON.stringify({ emergency_priority: emergencyPriority, override_reason: overrideReason }),
    }),
  corporatePasses: () => api<CorporatePass[]>("/corporate/passes"),
  lookupCorporatePass: (parkingLotId: string, passCode: string) =>
    api<CorporatePass>(`/corporate/passes/lookup?parking_lot_id=${encodeURIComponent(parkingLotId)}&pass_code=${encodeURIComponent(passCode)}`),
  managedLots: () => api<ParkingLot[]>("/parking/managed-lots"),
  createVisitorPass: (body: {
    parking_lot_id: string;
    pass_type: "visitor";
    visitor_name: string;
    visitor_phone?: string;
    starts_at: string;
    expires_at: string;
  }) => api<CorporatePass>("/corporate/passes", { method: "POST", body: JSON.stringify(body) }),
  revokeCorporatePass: (id: string) =>
    api<CorporatePass>(`/corporate/passes/${id}/revoke`, { method: "POST" }),
  analytics: () =>
    api<{ locations: number; capacity: number; occupied: number; occupancy_rate: number; revenue: string; bookings: number; peak_entry_hour: number | null; overstay_sessions: number }>(
      "/owner/analytics",
    ),
  reportIncident: (body: { parking_lot_id: string; category: string; description: string }) =>
    api<{ id: string }>("/incidents", { method: "POST", body: JSON.stringify(body) }),
};
