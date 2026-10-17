import { Logo } from "@/components/Logo";

const POINTS = [
  ["Rasm orqali qidiruv", "Xaridor rasm yuklaydi — AI katalogingizdan mosini topadi."],
  ["Qondirilmagan talab", "Qidirilgan, lekin do'koningizda yo'q tovarlarni ko'ring."],
  ["Yo'qotilgan daromad", "Tashlab ketilgan savatlar va konversiya voronkasi."],
];

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="grid min-h-screen lg:grid-cols-[1fr_minmax(0,560px)]">
      <div className="relative hidden overflow-hidden bg-[#160b33] p-12 text-white lg:flex lg:flex-col lg:justify-between">
        <div className="pointer-events-none absolute -left-24 -top-24 h-96 w-96 rounded-full bg-violet-600/40 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-32 right-0 h-[28rem] w-[28rem] rounded-full bg-fuchsia-500/25 blur-3xl" />
        <div className="relative"><Logo /></div>
        <div className="relative max-w-lg">
          <h2 className="text-4xl font-semibold leading-tight tracking-tight">Xaridor nimani izlayotganini ko'ring — va uni soting.</h2>
          <ul className="mt-10 space-y-5">
            {POINTS.map(([t, d]) => (
              <li key={t} className="flex gap-4">
                <span className="mt-1 h-2 w-2 flex-none rounded-full bg-fuchsia-400" />
                <div><p className="font-semibold">{t}</p><p className="text-sm text-white/70">{d}</p></div>
              </li>
            ))}
          </ul>
        </div>
        <p className="relative text-xs text-white/50">Bitta &lt;script&gt; tegi bilan istalgan saytga ulanadi.</p>
      </div>
      <div className="flex items-center justify-center px-5 py-12">
        <div className="w-full max-w-[400px]">
          <div className="mb-8 lg:hidden"><Logo /></div>
          {children}
        </div>
      </div>
    </div>
  );
}
