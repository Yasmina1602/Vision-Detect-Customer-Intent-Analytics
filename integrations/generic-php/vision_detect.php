<?php
/**
 * Vision Detect — oddiy PHP sayt uchun server tomoni (plaginsiz).
 *
 * 1) Layout'da </body> oldiga:
 *    <script src="https://API/cdn/v1/loader.js" data-key="pk_live_xxx" async></script>
 * 2) Buyurtma yaratilgandan keyin: vd_send_purchase($orderId, $userId, $items, 'UZS');
 * 3) (ixtiyoriy) Marketing kampaniyasini qabul qilish: vd_receive_campaign() — pastda.
 */

const VD_API = 'http://127.0.0.1:8000';         // production: https://api.vision.uz
const VD_SECRET_KEY = 'sk_live_xxx';             // Integratsiya → kalitlarni yangilashda bir marta ko'rsatiladi
const VD_WEBHOOK_SECRET = 'whsec_xxx';           // Integratsiya → "Webhook maxfiy kalitini ko'rsatish"

/** Xarid hodisasi. Xato bo'lsa buyurtma baribir davom etadi (timeout 3 s). */
function vd_send_purchase(string $orderId, ?string $userId, array $items, string $currency = 'UZS'): bool
{
    $payload = json_encode([
        'event_id'     => vd_uuid(),
        'type'         => 'PURCHASE',
        'order_ref'    => $orderId,
        'customer_ref' => $userId ? 'u_' . $userId : null,   // ichki ID — e-mail/telefon EMAS
        'session_id'   => $_COOKIE['vd_sid'] ?? null,        // vidjet qo'ygan cookie
        'currency'     => $currency,
        'items'        => $items,                             // [['id' => '7', 'qty' => 1, 'price_minor' => 12900000]]
    ]);
    $ts = (string) time();
    $ch = curl_init(VD_API . '/v1/server/events');
    curl_setopt_array($ch, [
        CURLOPT_POST           => true,
        CURLOPT_POSTFIELDS     => $payload,
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_TIMEOUT        => 3,
        CURLOPT_HTTPHEADER     => [
            'Content-Type: application/json',
            'Authorization: Bearer ' . VD_SECRET_KEY,
            'X-Timestamp: ' . $ts,
            'X-Signature: ' . hash_hmac('sha256', $ts . '.' . $payload, VD_WEBHOOK_SECRET),
        ],
    ]);
    curl_exec($ch);
    $ok = curl_getinfo($ch, CURLINFO_HTTP_CODE) < 300;
    curl_close($ch);
    return $ok;
}

/**
 * Kampaniya webhook'ini qabul qilish (Dashboard → Kampaniyalar → Marketing webhook URL = shu skript manzili).
 * Biz xaridorning kontaktini bilmaymiz — siz customer_ref bo'yicha o'z bazangizdan topib yuborasiz.
 */
function vd_receive_campaign(): void
{
    $body = file_get_contents('php://input');
    $ts = $_SERVER['HTTP_X_TIMESTAMP'] ?? '';
    $sig = $_SERVER['HTTP_X_SIGNATURE'] ?? '';
    if (abs(time() - (int) $ts) > 300 || !hash_equals(hash_hmac('sha256', $ts . '.' . $body, VD_WEBHOOK_SECRET), $sig)) {
        http_response_code(401);
        exit('bad signature');
    }
    $data = json_decode($body, true);
    foreach ($data['recipients'] as $r) {
        $userId = preg_replace('/^u_/', '', $r['customer_ref']);
        // $user = $db->query("SELECT phone, email FROM users WHERE id = ?", [$userId]);
        // send_sms($user['phone'], $data['campaign']['title'] . ' ' . $r['products'][0]['url']);
    }
    http_response_code(200);
    echo json_encode(['ok' => true]);
}

function vd_uuid(): string
{
    $d = random_bytes(16);
    $d[6] = chr(ord($d[6]) & 0x0f | 0x40);
    $d[8] = chr(ord($d[8]) & 0x3f | 0x80);
    return vsprintf('%s%s-%s-%s-%s-%s%s%s', str_split(bin2hex($d), 4));
}
