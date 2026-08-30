import { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { useCart } from "@/context/CartContext";
import { Avatar } from "@/components/common/Avatar";
import { formatBeans } from "@/utils/assets";

const NAV_LINKS = [
  { to: "/", label: "Marketplace", end: true },
  { to: "/history", label: "Purchase History", end: false },
  { to: "/giveaway", label: "Giveaway", end: false },
];

function NavItem({ to, label, end }: { to: string; label: string; end: boolean }) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        `rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
          isActive ? "bg-brand-50 text-brand-700" : "text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900"
        }`
      }
    >
      {label}
    </NavLink>
  );
}

export function Navbar() {
  const { user, logout } = useAuth();
  const { itemCount } = useCart();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  if (!user) return null;

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <header className="sticky top-0 z-40 border-b border-zinc-200 bg-white/80 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <div className="flex items-center gap-6">
          <NavLink to="/" className="flex items-center gap-2 font-bold text-zinc-900">
            <img src="/bean-icon.png" alt="" className="h-8 w-8 shrink-0 rounded-lg object-cover object-center" />
            <span className="hidden sm:inline">Chumber</span>
          </NavLink>
          <nav className="hidden items-center gap-1 md:flex">
            {NAV_LINKS.map((link) => (
              <NavItem key={link.to} {...link} />
            ))}
            {user.role === "admin" && (
              <NavLink
                to="/admin"
                className={({ isActive }) =>
                  `rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                    isActive ? "bg-zinc-900 text-white" : "text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900"
                  }`
                }
              >
                Admin Dashboard
              </NavLink>
            )}
          </nav>
        </div>

        <div className="flex items-center gap-2 sm:gap-3">
          <div className="flex items-center gap-1 rounded-full bg-zinc-100 px-2.5 py-1.5 text-xs font-semibold text-zinc-800 sm:gap-1.5 sm:px-3 sm:text-sm">
            <img src="/bean-icon.png" alt="" className="h-4 w-4 shrink-0 object-contain object-center" />
            {formatBeans(user.balance)}
          </div>

          <NavLink to="/cart" className="relative rounded-lg p-2 text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900" aria-label="Cart">
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 3h1.386c.51 0 .955.343 1.087.835l.383 1.437M7.5 14.25a3 3 0 00-3 3h15.75m-12.75-3h11.218c1.121-2.3 1.994-4.694 2.602-7.152.084-.341-.16-.68-.502-.68H5.106M7.5 14.25L5.106 5.272M6 20.25a.75.75 0 11-1.5 0 .75.75 0 011.5 0zm12.75 0a.75.75 0 11-1.5 0 .75.75 0 011.5 0z" />
            </svg>
            {itemCount > 0 && (
              <span className="absolute -right-0.5 -top-0.5 flex h-[18px] min-w-[18px] items-center justify-center rounded-full bg-brand-600 px-1 text-[10px] font-bold text-white">
                {itemCount}
              </span>
            )}
          </NavLink>

          <div className="relative">
            <button onClick={() => setMenuOpen((v) => !v)} className="flex items-center rounded-full ring-offset-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-600">
              <Avatar src={user.avatar_url} name={user.full_name} size="sm" />
            </button>
            {menuOpen && (
              <>
                <div className="fixed inset-0 z-10" onClick={() => setMenuOpen(false)} />
                <div className="absolute right-0 z-20 mt-2 w-52 animate-fade-in rounded-xl border border-zinc-200 bg-white py-1.5 shadow-lg">
                  <div className="border-b border-zinc-100 px-3.5 py-2.5">
                    <p className="truncate text-sm font-semibold text-zinc-900">{user.full_name}</p>
                    <p className="truncate text-xs text-zinc-500">@{user.username}</p>
                  </div>
                  <NavLink to="/profile" onClick={() => setMenuOpen(false)} className="block px-3.5 py-2 text-sm text-zinc-700 hover:bg-zinc-50">
                    Profile
                  </NavLink>
                  <NavLink to="/history" onClick={() => setMenuOpen(false)} className="block px-3.5 py-2 text-sm text-zinc-700 hover:bg-zinc-50 md:hidden">
                    Purchase History
                  </NavLink>
                  <button onClick={handleLogout} className="block w-full px-3.5 py-2 text-left text-sm text-red-600 hover:bg-red-50">
                    Log out
                  </button>
                </div>
              </>
            )}
          </div>

          <button onClick={() => setMobileOpen((v) => !v)} className="rounded-lg p-2 text-zinc-600 hover:bg-zinc-100 md:hidden" aria-label="Menu">
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5M3.75 17.25h16.5" />
            </svg>
          </button>
        </div>
      </div>

      {mobileOpen && (
        <nav className="flex flex-col gap-1 border-t border-zinc-100 px-4 py-3 md:hidden">
          {NAV_LINKS.map((link) => (
            <div key={link.to} onClick={() => setMobileOpen(false)}>
              <NavItem {...link} />
            </div>
          ))}
          {user.role === "admin" && (
            <NavLink to="/admin" onClick={() => setMobileOpen(false)} className="rounded-lg px-3 py-2 text-sm font-medium text-zinc-600 hover:bg-zinc-100">
              Admin Dashboard
            </NavLink>
          )}
        </nav>
      )}
    </header>
  );
}
