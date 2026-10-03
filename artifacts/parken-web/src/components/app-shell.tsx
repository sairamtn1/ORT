import { motion } from "framer-motion";
import { Bell, CarFront, ChevronRight, CircleUserRound, LayoutDashboard, LogOut, Map, Menu, ParkingSquare, Search, Settings2, ShieldCheck, SlidersHorizontal, X } from "lucide-react";
import { useState, type ReactNode } from "react";
import { Link, useLocation } from "wouter";
import { useAuth } from "@/lib/auth";
import { Button } from "./ui";

const customerNav = [
  { href: "/dashboard", label: "Overview", icon: LayoutDashboard },
  { href: "/search", label: "Find parking", icon: Search },
  { href: "/map", label: "Map view", icon: Map },
  { href: "/bookings", label: "My bookings", icon: CarFront },
];
const ownerNav = [
  { href: "/owner", label: "Overview", icon: LayoutDashboard },
  { href: "/owner/parking", label: "Parking spaces", icon: ParkingSquare },
  { href: "/owner/analytics", label: "Analytics", icon: SlidersHorizontal },
];

function NavGroup({ title, items, current }: { title: string; items: typeof customerNav; current: string }) {
  return <div className="mt-8"><p className="px-3 text-[10px] font-bold uppercase tracking-[0.18em] text-slate-400">{title}</p><nav className="mt-2 grid gap-1">{items.map(({ href, label, icon: Icon }) => <Link key={href} href={href} className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition ${current === href ? "bg-slate-950 text-white shadow-lg shadow-slate-950/10" : "text-slate-500 hover:bg-slate-100 hover:text-slate-950"}`} data-testid={`link-${label.toLowerCase().replaceAll(" ", "-")}`}><Icon size={17} strokeWidth={1.8} /><span>{label}</span>{current === href && <ChevronRight className="ml-auto" size={15} />}</Link>)}</nav></div>;
}

export function AppShell({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  const [location, setLocation] = useLocation();
  const [open, setOpen] = useState(false);
  const isOwner = user?.role === "owner";
  const isAdmin = user?.role === "admin";
  const nav = isOwner ? ownerNav : customerNav;

  return <div className="min-h-screen bg-[#f7f8fa] text-slate-950">
    <aside className={`fixed inset-y-0 left-0 z-40 w-72 border-r border-slate-200 bg-white px-5 py-6 transition-transform lg:translate-x-0 ${open ? "translate-x-0" : "-translate-x-full"}`}>
      <div className="flex items-center justify-between"><Link href="/" className="flex items-center gap-3" data-testid="link-shell-logo"><span className="grid h-9 w-9 place-items-center rounded-xl bg-slate-950 text-white"><ParkingSquare size={19} /></span><span className="text-lg font-semibold tracking-[-0.04em]">ORT</span></Link><button className="rounded-lg p-2 text-slate-400 lg:hidden" onClick={() => setOpen(false)} data-testid="button-close-menu"><X size={18} /></button></div>
      <div className="mt-10 rounded-2xl bg-slate-50 p-4"><p className="text-xs font-medium text-slate-400">Signed in as</p><p className="mt-1 truncate text-sm font-semibold text-slate-900">{user?.full_name}</p><p className="mt-0.5 text-xs capitalize text-slate-500">{isAdmin ? "Platform admin" : isOwner ? "Parking owner" : "Customer"}</p></div>
      <NavGroup title={isAdmin ? "Administration" : "Workspace"} items={isAdmin ? [{ href: "/admin", label: "Admin dashboard", icon: ShieldCheck }] : nav} current={location} />
      {!isAdmin && <div className="mt-8"><p className="px-3 text-[10px] font-bold uppercase tracking-[0.18em] text-slate-400">Account</p><nav className="mt-2 grid gap-1"><Link href="/notifications" className="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-slate-500 hover:bg-slate-100 hover:text-slate-950" data-testid="link-notifications"><Bell size={17} /><span>Notifications</span></Link><Link href="/settings" className="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-slate-500 hover:bg-slate-100 hover:text-slate-950" data-testid="link-settings"><Settings2 size={17} /><span>Settings</span></Link></nav></div>}
      <button onClick={() => { logout(); setLocation("/"); }} className="absolute bottom-6 left-5 right-5 flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-slate-500 hover:bg-rose-50 hover:text-rose-700" data-testid="button-logout"><LogOut size={17} /><span>Sign out</span></button>
    </aside>
    {open && <button className="fixed inset-0 z-30 bg-slate-950/20 lg:hidden" onClick={() => setOpen(false)} data-testid="button-dismiss-menu" />}
    <main className="lg:pl-72">
      <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-slate-200/80 bg-[#f7f8fa]/90 px-5 backdrop-blur-xl sm:px-8"><button className="rounded-xl p-2 text-slate-500 lg:hidden" onClick={() => setOpen(true)} data-testid="button-open-menu"><Menu size={21} /></button><div className="hidden text-sm text-slate-400 sm:block">{isAdmin ? "Platform control center" : isOwner ? "Manage your parking business" : "Your parking, made simple"}</div><div className="ml-auto flex items-center gap-3"><Link href="/notifications" className="relative rounded-xl p-2.5 text-slate-500 transition hover:bg-white hover:text-slate-950" data-testid="button-header-notifications"><Bell size={18} /></Link><div className="hidden h-8 w-px bg-slate-200 sm:block" /><Link href="/settings" className="flex items-center gap-2 text-sm font-medium text-slate-700" data-testid="link-header-profile"><span className="grid h-8 w-8 place-items-center rounded-full bg-slate-200 text-slate-600"><CircleUserRound size={17} /></span><span className="hidden sm:inline">{user?.full_name?.split(" ")[0]}</span></Link></div></header>
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35 }} className="mx-auto max-w-[1440px] px-5 py-8 sm:px-8 lg:px-10">{children}</motion.div>
    </main>
  </div>;
}

export function PublicNav() {
  return <header className="absolute inset-x-0 top-0 z-20 mx-auto flex max-w-7xl items-center justify-between px-6 py-6 lg:px-10"><Link href="/" className="flex items-center gap-3" data-testid="link-public-logo"><span className="grid h-9 w-9 place-items-center rounded-xl bg-slate-950 text-white"><ParkingSquare size={19} /></span><span className="text-lg font-semibold tracking-[-0.04em]">ORT</span></Link><div className="flex items-center gap-3"><Link href="/login" className="rounded-xl px-4 py-2.5 text-sm font-semibold text-slate-600 hover:bg-white/70" data-testid="link-public-login">Sign in</Link><Link href="/signup" className="rounded-xl bg-slate-950 px-4 py-2.5 text-sm font-semibold text-white shadow-lg shadow-slate-950/10 hover:bg-slate-800" data-testid="link-public-signup">Get started</Link></div></header>;
}