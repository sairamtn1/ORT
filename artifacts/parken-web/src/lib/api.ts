export type Role = "customer" | "owner" | "admin";
export type LotStatus = "draft" | "active" | "paused" | "archived";
export type SlotStatus = "available" | "occupied" | "maintenance";
export type BookingStatus = "pending" | "confirmed" | "cancelled" | "completed";

export interface User {
  id: string;
  email: string;
  full_name: string;
  phone?: string | null;
  role: Role;
  status: string;
  created_at: string;
  updated_at: string;
}
export interface Owner {
  id: string;
  user_id: string;
  business_name?: string | null;
  government_id?: string | null;
  verified: boolean;
  created_at: string;
  updated_at: string;
}
export interface ParkingLot {
  id: string;
  owner_id: string;
  name: string;
  address: string;
  city: string;
  latitude: number;
  longitude: number;
  description?: string | null;
  status: LotStatus;
  created_at: string;
  updated_at: string;
}
export interface ParkingSlot {
  id: string;
  parking_lot_id: string;
  slot_number: string;
  vehicle_type: string;
  hourly_rate: number;
  status: SlotStatus;
  created_at: string;
  updated_at: string;
}
export interface Booking {
  id: string;
  customer_id: string;
  parking_slot_id: string;
  starts_at: string;
  ends_at: string;
  total_amount: number;
  status: BookingStatus;
  created_at: string;
  updated_at: string;
}
export interface Payment {
  id: string;
  booking_id: string;
  amount: number;
  currency: string;
  provider?: string | null;
  provider_reference?: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}
export interface Review {
  id: string;
  booking_id: string;
  customer_id: string;
  rating: number;
  comment?: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}
export interface Notification {
  id: string;
  user_id: string;
  title: string;
  message: string;
  status: string;
  read_at?: string | null;
  created_at: string;
  updated_at: string;
}

const API_PREFIX = "/api/v1";

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = localStorage.getItem("parken_access_token");
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`${API_PREFIX}${path}`, { ...options, headers });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail ?? `Request failed with ${response.status}`);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const api = {
  login: (body: { email: string; password: string }) =>
    apiFetch<{ access_token: string; expires_in: number }>("/auth/login", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  register: (body: {
    email: string;
    password: string;
    full_name: string;
    phone?: string;
    role: Role;
  }) => apiFetch<User>("/auth/register", { method: "POST", body: JSON.stringify(body) }),
  me: () => apiFetch<User>("/auth/me"),
  lots: () => apiFetch<ParkingLot[]>("/parking-lots"),
  lot: (id: string) => apiFetch<ParkingLot>(`/parking-lots/${id}`),
  createLot: (body: Partial<ParkingLot>) =>
    apiFetch<ParkingLot>("/parking-lots", { method: "POST", body: JSON.stringify(body) }),
  updateLot: (id: string, body: Partial<ParkingLot>) =>
    apiFetch<ParkingLot>(`/parking-lots/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  deleteLot: (id: string) => apiFetch<void>(`/parking-lots/${id}`, { method: "DELETE" }),
  slots: (lotId?: string) =>
    apiFetch<ParkingSlot[]>(`/parking-slots${lotId ? `?parking_lot_id=${lotId}` : ""}`),
  createSlot: (body: Partial<ParkingSlot>) =>
    apiFetch<ParkingSlot>("/parking-slots", { method: "POST", body: JSON.stringify(body) }),
  updateSlot: (id: string, body: Partial<ParkingSlot>) =>
    apiFetch<ParkingSlot>(`/parking-slots/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  bookings: () => apiFetch<Booking[]>("/bookings"),
  createBooking: (body: Partial<Booking>) =>
    apiFetch<Booking>("/bookings", { method: "POST", body: JSON.stringify(body) }),
  updateBooking: (id: string, body: Partial<Booking>) =>
    apiFetch<Booking>(`/bookings/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  owners: () => apiFetch<Owner[]>("/owners"),
  createOwner: (body: Partial<Owner>) =>
    apiFetch<Owner>("/owners", { method: "POST", body: JSON.stringify(body) }),
  users: () => apiFetch<User[]>("/users"),
  admins: () => apiFetch<unknown[]>("/admins"),
  payments: () => apiFetch<Payment[]>("/payments"),
  reviews: () => apiFetch<Review[]>("/reviews"),
  notifications: () => apiFetch<Notification[]>("/notifications"),
};