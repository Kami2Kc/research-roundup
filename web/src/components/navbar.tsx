import Link from "next/link";
import NavbarButton from "@/components/ui/navbarButton";

const NAV = [
  { href: "/", label: "Issues" },
  { href: "/papers/", label: "Papers" },
  { href: "/sources/", label: "Sources" },
  { href: "/methodology/", label: "Methodology" },
];

const Navbar = () => {
  return (
    <header className="sticky z-100 top-0 bg-[#0b2545] text-white">
      <div className="mx-auto flex w-full max-w-6xl flex-wrap items-center justify-center xl:justify-between">
        <Link href="/" className="font-serif text-xl font-bold tracking-tight">
          The Research Roundup
        </Link>
        <nav className="h-full flex xl:gap-5 text-sm text-slate-300">
          {NAV.map((item) => (
            <NavbarButton key={item.href} href={item.href} label={item.label} />
          ))}
        </nav>
      </div>
    </header>
  );
};

export default Navbar;
