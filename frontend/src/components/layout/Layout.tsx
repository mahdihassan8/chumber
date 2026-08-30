import { Outlet } from "react-router-dom";
import { Navbar } from "@/components/layout/Navbar";

export function Layout() {
  return (
    <>
      <Navbar />
      <main className="flex flex-1 flex-col">
        <Outlet />
      </main>
    </>
  );
}
