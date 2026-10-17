"""Demo katalog uchun mahsulot illyustratsiyalari (SVG). Faqat seed/dev — haqiqiy do'konda rasm yuklanadi."""

_SHAPES = {
    "krossovka": '<path d="M60 250 C60 210 90 190 130 185 L190 150 C205 142 220 150 228 165 L250 200 C290 205 330 215 345 240 C352 255 345 272 325 275 L80 278 C66 278 60 268 60 250Z" fill="{c}"/>'
                 '<path d="M60 262 L345 262 C345 280 335 292 318 292 L82 292 C68 292 60 282 60 262Z" fill="#f8fafc" stroke="#cbd5e1" stroke-width="3"/>'
                 '<path d="M150 190 L170 215 M172 178 L192 203 M194 166 L214 191" stroke="#fff" stroke-width="7" stroke-linecap="round" opacity=".85"/>',
    "tufli": '<path d="M70 240 C80 215 120 205 170 210 C220 214 250 195 280 200 C320 206 345 230 340 255 L75 262 C64 262 64 250 70 240Z" fill="{c}"/>'
             '<rect x="70" y="258" width="275" height="16" rx="8" fill="#334155"/><rect x="300" y="250" width="30" height="40" rx="6" fill="#334155"/>',
    "etik": '<path d="M140 90 L230 90 L235 220 C285 222 330 235 340 262 L340 280 L110 280 L110 230 C125 215 135 180 140 90Z" fill="{c}"/>'
            '<rect x="108" y="278" width="234" height="16" rx="8" fill="#1f2937"/><path d="M150 110 L222 110" stroke="#fff" stroke-width="5" opacity=".5"/>',
    "shippak": '<ellipse cx="200" cy="230" rx="130" ry="55" fill="{c}"/><path d="M130 225 C160 170 240 170 270 225" stroke="#334155" stroke-width="18" fill="none" stroke-linecap="round"/>',
    "xudi": '<path d="M150 95 C160 70 240 70 250 95 L300 115 L345 230 L305 245 L285 195 L285 330 L115 330 L115 195 L95 245 L55 230 L100 115Z" fill="{c}"/>'
            '<path d="M160 100 C170 140 230 140 240 100" fill="none" stroke="#0f172a" stroke-opacity=".25" stroke-width="8"/>'
            '<rect x="160" y="230" width="80" height="45" rx="10" fill="#000" opacity=".12"/><path d="M185 140 L185 175 M215 140 L215 175" stroke="#fff" stroke-width="4" opacity=".8"/>',
    "sviter": '<path d="M150 90 C170 105 230 105 250 90 L305 115 L345 235 L305 248 L285 195 L285 320 L115 320 L115 195 L95 248 L55 235 L95 115Z" fill="{c}"/>'
              '<path d="M115 300 L285 300 M115 310 L285 310" stroke="#000" stroke-opacity=".15" stroke-width="4"/><path d="M160 92 C175 115 225 115 240 92" fill="none" stroke="#000" stroke-opacity=".2" stroke-width="6"/>',
    "futbolka": '<path d="M150 90 C170 110 230 110 250 90 L320 120 L345 175 L295 190 L290 320 L110 320 L105 190 L55 175 L80 120Z" fill="{c}"/>'
                '<path d="M160 92 C175 118 225 118 240 92" fill="none" stroke="#000" stroke-opacity=".18" stroke-width="6"/>',
    "ko'ylak": '<path d="M150 85 L200 120 L250 85 L320 115 L345 230 L300 240 L290 195 L290 330 L110 330 L110 195 L100 240 L55 230 L80 115Z" fill="{c}"/>'
               '<path d="M200 120 L200 330" stroke="#000" stroke-opacity=".18" stroke-width="4"/><circle cx="200" cy="160" r="5" fill="#fff"/><circle cx="200" cy="205" r="5" fill="#fff"/><circle cx="200" cy="250" r="5" fill="#fff"/>',
    "shim": '<path d="M130 80 L270 80 L285 340 L215 340 L200 160 L185 340 L115 340Z" fill="{c}"/><rect x="130" y="80" width="140" height="20" fill="#000" opacity=".15"/>',
    "kurtka": '<path d="M145 85 L200 105 L255 85 L320 115 L350 300 L300 310 L290 200 L290 330 L110 330 L110 200 L100 310 L50 300 L80 115Z" fill="{c}"/>'
              '<path d="M200 105 L200 330" stroke="#e2e8f0" stroke-width="6"/><rect x="130" y="230" width="50" height="10" rx="5" fill="#000" opacity=".2"/><rect x="220" y="230" width="50" height="10" rx="5" fill="#000" opacity=".2"/>',
    "yubka": '<path d="M150 110 L250 110 L320 320 L80 320Z" fill="{c}"/><rect x="150" y="100" width="100" height="22" rx="4" fill="#000" opacity=".15"/>',
    "kostyum": '<path d="M145 85 L200 150 L255 85 L320 115 L345 320 L55 320 L80 115Z" fill="{c}"/><path d="M200 150 L175 200 L200 330 L225 200Z" fill="#f8fafc"/>',
    "sumka": '<path d="M150 150 C150 90 250 90 250 150" fill="none" stroke="{c}" stroke-width="14"/><rect x="85" y="140" width="230" height="180" rx="26" fill="{c}"/>'
             '<rect x="85" y="140" width="230" height="50" rx="20" fill="#000" opacity=".12"/><rect x="185" y="175" width="30" height="22" rx="5" fill="#fbbf24"/>',
    "ryukzak": '<rect x="115" y="95" width="170" height="230" rx="50" fill="{c}"/><rect x="140" y="215" width="120" height="80" rx="18" fill="#000" opacity=".15"/>'
               '<path d="M165 95 C165 60 235 60 235 95" fill="none" stroke="{c}" stroke-width="14"/><rect x="185" y="230" width="30" height="8" rx="4" fill="#fff" opacity=".7"/>',
    "hamyon": '<rect x="90" y="140" width="220" height="140" rx="20" fill="{c}"/><rect x="230" y="190" width="80" height="45" rx="12" fill="#000" opacity=".18"/><circle cx="255" cy="212" r="7" fill="#fbbf24"/>',
    "soat": '<rect x="170" y="60" width="60" height="90" rx="10" fill="#334155"/><rect x="170" y="250" width="60" height="90" rx="10" fill="#334155"/>'
            '<circle cx="200" cy="200" r="78" fill="{c}"/><circle cx="200" cy="200" r="62" fill="#0f172a"/>'
            '<path d="M200 200 L200 160 M200 200 L228 214" stroke="#fff" stroke-width="7" stroke-linecap="round"/>',
    "ko'zoynak": '<circle cx="135" cy="210" r="58" fill="{c}"/><circle cx="265" cy="210" r="58" fill="{c}"/>'
                 '<path d="M193 205 C200 192 210 192 207 205" stroke="#1f2937" stroke-width="8" fill="none"/><path d="M77 200 L45 180 M323 200 L355 180" stroke="#1f2937" stroke-width="8" stroke-linecap="round"/>'
                 '<path d="M110 190 L140 175" stroke="#fff" stroke-width="7" opacity=".5" stroke-linecap="round"/>',
    "kepka": '<path d="M110 230 C110 140 290 140 290 230Z" fill="{c}"/><path d="M270 225 L350 240 C355 250 345 258 330 255 L260 240Z" fill="{c}"/><circle cx="200" cy="148" r="8" fill="#000" opacity=".3"/>',
    "kamar": '<rect x="50" y="185" width="300" height="34" rx="10" fill="{c}"/><rect x="160" y="175" width="70" height="54" rx="8" fill="none" stroke="#fbbf24" stroke-width="10"/>',
    "naushnik": '<path d="M110 230 C110 120 290 120 290 230" fill="none" stroke="{c}" stroke-width="18"/><rect x="85" y="210" width="55" height="90" rx="22" fill="{c}"/><rect x="260" y="210" width="55" height="90" rx="22" fill="{c}"/>',
    "telefon": '<rect x="135" y="65" width="130" height="270" rx="26" fill="{c}"/><rect x="147" y="85" width="106" height="220" rx="12" fill="#0f172a"/><circle cx="200" cy="320" r="7" fill="#64748b"/>',
    "noutbuk": '<rect x="95" y="100" width="210" height="140" rx="12" fill="{c}"/><rect x="107" y="112" width="186" height="116" rx="6" fill="#0f172a"/><path d="M65 255 L335 255 L315 280 L85 280Z" fill="{c}"/>',
    "chashka": '<path d="M110 140 L270 140 L255 310 C254 322 245 330 233 330 L147 330 C135 330 126 322 125 310Z" fill="{c}"/><path d="M268 175 C320 175 320 260 262 260" fill="none" stroke="{c}" stroke-width="16"/>',
    "atir": '<rect x="175" y="70" width="50" height="45" rx="6" fill="#334155"/><rect x="120" y="115" width="160" height="210" rx="34" fill="{c}" opacity=".9"/><rect x="150" y="190" width="100" height="60" rx="8" fill="#fff" opacity=".7"/>',
}
_DEFAULT = '<rect x="90" y="90" width="220" height="220" rx="40" fill="{c}"/>'


def product_svg(type_: str | None, color_hex: str, bg: str = "#f1f5f9") -> str:
    shape = _SHAPES.get(type_ or "", _DEFAULT).replace("{c}", color_hex)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400">'
            f'<defs><radialGradient id="b" cx="50%" cy="40%" r="70%"><stop offset="0" stop-color="#ffffff"/>'
            f'<stop offset="1" stop-color="{bg}"/></radialGradient></defs>'
            f'<rect width="400" height="400" fill="url(#b)"/>'
            f'<ellipse cx="200" cy="345" rx="130" ry="14" fill="#0f172a" opacity=".08"/>'
            f'<g stroke-linejoin="round">{shape}</g></svg>')
