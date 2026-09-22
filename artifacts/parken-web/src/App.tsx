import { useEffect, type ReactNode } from "react";
import { Link, Route, Router as WouterRouter, Switch, useLocation } from "wouter";
import { ErrorBoundary } from "@/components/error-boundary";
import { AppShell } from "@/components/app-shell";
import { AuthProvider, useAuth } from "@/lib/auth";
import { AdminDashboard } from "@/pages/admin";
import { CustomerDashboard, SearchPage, MapPage, ParkingDetail, ReservePage, BookingsPage } from "@/pages/customer";
import { LandingPage, LoginPage, SignupPage } from "@/pages/public";
import { OwnerDashboard, OwnerParking, OwnerAnalytics } from "@/pages/owner";
import { NotificationsPage, SettingsPage } from "@/pages/misc";

function Protected({ children, roles }: { children: ReactNode; roles?: string[] }) {
  const { user, loading } = useAuth();
  const [, setLocation] = useLocation();
  useEffect(() => { if (!loading && !user) setLocation("/login"); }, [loading, user, setLocation]);
  if (loading) return <div className="grid min-h-screen place-items-center bg-[#f7f8fa]"><div className="h-8 w-8 animate-spin rounded-full border-2 border-slate-200 border-t-slate-950" /></div>;
  if (!user || (roles && !roles.includes(user.role))) return null;
  return <>{children}</>;
}

function NotFound() {
  return <div className="grid min-h-screen place-items-center bg-[#f7f8fa] p-6 text-center"><div><p className="text-sm font-bold uppercase tracking-[.18em] text-slate-400">404</p><h1 className="mt-3 text-4xl font-semibold tracking-[-.06em]">That page moved.</h1><p className="mt-3 text-sm text-slate-500">Let’s get you back to something useful.</p><Link href="/" className="mt-6 inline-flex rounded-xl bg-slate-950 px-4 py-3 text-sm font-semibold text-white" data-testid="link-not-found-home">Back home</Link></div></div>;
}

function Router() {
  const [location] = useLocation();
  return <ErrorBoundary resetKey={location}><Switch>
    <Route path="/" component={LandingPage} />
    <Route path="/login" component={LoginPage} />
    <Route path="/signup" component={SignupPage} />
    <Route path="/dashboard">{() => <Protected roles={["customer"]}><CustomerDashboard /></Protected>}</Route>
    <Route path="/search">{() => <Protected roles={["customer"]}><SearchPage /></Protected>}</Route>
    <Route path="/map">{() => <Protected roles={["customer"]}><MapPage /></Protected>}</Route>
    <Route path="/parking/:id">{() => <Protected roles={["customer"]}><ParkingDetail /></Protected>}</Route>
    <Route path="/reserve/:slotId">{() => <Protected roles={["customer"]}><ReservePage /></Protected>}</Route>
    <Route path="/bookings">{() => <Protected roles={["customer"]}><BookingsPage /></Protected>}</Route>
    <Route path="/owner">{() => <Protected roles={["owner"]}><OwnerDashboard /></Protected>}</Route>
    <Route path="/owner/parking">{() => <Protected roles={["owner"]}><OwnerParking /></Protected>}</Route>
    <Route path="/owner/analytics">{() => <Protected roles={["owner"]}><OwnerAnalytics /></Protected>}</Route>
    <Route path="/admin">{() => <Protected roles={["admin"]}><AdminDashboard /></Protected>}</Route>
    <Route path="/notifications">{() => <Protected><NotificationsPage /></Protected>}</Route>
    <Route path="/settings">{() => <Protected><SettingsPage /></Protected>}</Route>
    <Route component={NotFound} />
  </Switch></ErrorBoundary>;
}

export default function App() {
  return <AuthProvider><WouterRouter base={import.meta.env.BASE_URL.replace(/\/$/, "")}><Router /></WouterRouter></AuthProvider>;
}
