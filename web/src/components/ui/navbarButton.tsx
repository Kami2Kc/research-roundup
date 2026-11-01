import Link from "next/link";

const NavbarButton = ({ href, label }: { href: string; label: string }) => {
  return (
    <Link
      href={href}
      className="h-full p-4 hover:bg-[#103562] hover:text-white duration-150"
    >
      {label}
    </Link>
  );
};

export default NavbarButton;
