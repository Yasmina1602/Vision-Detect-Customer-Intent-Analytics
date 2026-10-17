<?php
/**
 * Plugin Name: Vision Detect — rasm orqali qidiruv va analitika
 * Description: Vidjetni ulaydi, katalog feed'ini ochadi, buyurtmalarni HMAC imzoli webhook bilan yuboradi, vd_sid ni buyurtmaga yozadi.
 * Version:     1.0.0
 * Requires PHP: 7.4
 * WC requires at least: 6.0
 * License:     MIT
 *
 * Plagin faqat 3 ish qiladi (README 12-bo'lim):
 *   1) /wp-json/vision-detect/v1/feed — mahsulotlar feed'i (JSON)
 *   2) Buyurtma yaratilganda POST {API}/v1/server/webhooks/woocommerce?key=pk_… (HMAC, 3 s timeout, xatoda buyurtma to'xtamaydi)
 *   3) vd_sid cookie'sini buyurtma meta'siga (_vd_sid) yozadi — atribusiya uchun
 * Username/e-mail/telefon UZATILMAYDI — faqat WooCommerce ichki customer_id (customer_ref).
 */

if (!defined('ABSPATH')) {
    exit;
}

const VD_OPT = 'vision_detect_settings';

function vd_opt($key, $default = '') {
    $o = get_option(VD_OPT, []);
    return isset($o[$key]) && $o[$key] !== '' ? $o[$key] : $default;
}

/* ---------- Sozlamalar sahifasi ---------- */
add_action('admin_menu', function () {
    add_options_page('Vision Detect', 'Vision Detect', 'manage_options', 'vision-detect', 'vd_settings_page');
});

add_action('admin_init', function () {
    register_setting('vision_detect', VD_OPT, [
        'sanitize_callback' => function ($v) {
            return [
                'api_url'        => esc_url_raw(rtrim($v['api_url'] ?? '', '/')),
                'public_key'     => sanitize_text_field($v['public_key'] ?? ''),
                'webhook_secret' => sanitize_text_field($v['webhook_secret'] ?? ''),
            ];
        },
    ]);
});

function vd_settings_page() {
    $feed = rest_url('vision-detect/v1/feed');
    ?>
    <div class="wrap">
        <h1>Vision Detect</h1>
        <p>Kalitlarni Vision Detect dashboard → <b>Integratsiya</b> sahifasidan oling.</p>
        <form method="post" action="options.php">
            <?php settings_fields('vision_detect'); ?>
            <table class="form-table">
                <tr><th>API manzili</th><td><input class="regular-text" name="<?php echo VD_OPT; ?>[api_url]" value="<?php echo esc_attr(vd_opt('api_url', 'https://api.vision.uz')); ?>"></td></tr>
                <tr><th>Public key</th><td><input class="regular-text" name="<?php echo VD_OPT; ?>[public_key]" value="<?php echo esc_attr(vd_opt('public_key')); ?>" placeholder="pk_live_…"></td></tr>
                <tr><th>Webhook secret</th><td><input class="regular-text" type="password" name="<?php echo VD_OPT; ?>[webhook_secret]" value="<?php echo esc_attr(vd_opt('webhook_secret')); ?>" placeholder="whsec_…"></td></tr>
            </table>
            <?php submit_button(); ?>
        </form>
        <h2>Katalog feed URL</h2>
        <p>Dashboard → Katalog → Feed manbasi maydoniga kiriting (format: JSON):</p>
        <code><?php echo esc_html($feed); ?></code>
    </div>
    <?php
}

/* ---------- 1) Vidjet: bitta teg ---------- */
add_action('wp_footer', function () {
    $api = vd_opt('api_url');
    $pk = vd_opt('public_key');
    if (!$api || !$pk) {
        return;
    }
    printf('<script src="%s/cdn/v1/loader.js" data-key="%s" async></script>' . "\n", esc_url($api), esc_attr($pk));
    // Login bo'lgan xaridor: faqat ichki neytral ID
    if (is_user_logged_in()) {
        printf('<script>window.addEventListener("load",function(){window.VisionAnalytics&&VisionAnalytics.identify&&VisionAnalytics.identify("%d")});</script>' . "\n", get_current_user_id());
    }
}, 99);

/* ---------- 2) Katalog feed ---------- */
add_action('rest_api_init', function () {
    register_rest_route('vision-detect/v1', '/feed', [
        'methods'             => 'GET',
        'permission_callback' => '__return_true',
        'callback'            => function () {
            $out = [];
            $page = 1;
            do {
                $products = wc_get_products(['status' => 'publish', 'limit' => 200, 'page' => $page, 'type' => ['simple', 'variable']]);
                foreach ($products as $p) {
                    $cats = wp_get_post_terms($p->get_id(), 'product_cat', ['fields' => 'names']);
                    $color = $p->get_attribute('pa_color') ?: $p->get_attribute('color') ?: $p->get_attribute('rang');
                    $img = wp_get_attachment_image_url($p->get_image_id(), 'large');
                    $out[] = [
                        'id'            => (string) $p->get_id(),
                        'name'          => $p->get_name(),
                        'description'   => wp_strip_all_tags($p->get_short_description() ?: $p->get_description()),
                        'category'      => $cats[0] ?? '',
                        'color'         => $color,
                        'price'         => $p->get_price(),
                        'regular_price' => $p->is_on_sale() ? $p->get_regular_price() : '',
                        'currency'      => get_woocommerce_currency(),
                        'image_url'     => $img ?: '',
                        'product_url'   => get_permalink($p->get_id()),
                        'in_stock'      => $p->is_in_stock(),
                        'stock_qty'     => $p->managing_stock() ? (int) $p->get_stock_quantity() : '',
                    ];
                }
                $page++;
            } while (count($products) === 200);
            return rest_ensure_response(['products' => $out]);
        },
    ]);
});

/* ---------- 3) vd_sid → buyurtma meta ---------- */
add_action('woocommerce_checkout_create_order', function ($order) {
    if (!empty($_COOKIE['vd_sid'])) {
        $order->update_meta_data('_vd_sid', sanitize_text_field(wp_unslash($_COOKIE['vd_sid'])));
    }
});

/* ---------- Buyurtma webhook (server→server, HMAC) ---------- */
function vd_send_order($order_id) {
    $api = vd_opt('api_url');
    $pk = vd_opt('public_key');
    $secret = vd_opt('webhook_secret');
    $order = wc_get_order($order_id);
    if (!$api || !$pk || !$secret || !$order || $order->get_meta('_vd_sent')) {
        return;
    }
    $items = [];
    foreach ($order->get_items() as $item) {
        $items[] = [
            'product_id' => $item->get_product_id(),
            'quantity'   => $item->get_quantity(),
            'price'      => $order->get_item_subtotal($item, false, false),
            'name'       => $item->get_name(),
        ];
    }
    $payload = wp_json_encode([
        'id'          => $order->get_id(),
        'currency'    => $order->get_currency(),
        'customer_id' => $order->get_customer_id(),          // neytral ID; e-mail/telefon yuborilmaydi
        'meta_data'   => [['key' => '_vd_sid', 'value' => $order->get_meta('_vd_sid')]],
        'line_items'  => $items,
    ]);
    $ts = (string) time();
    $sig = hash_hmac('sha256', $ts . '.' . $payload, $secret);
    $res = wp_remote_post($api . '/v1/server/webhooks/woocommerce?key=' . rawurlencode($pk), [
        'timeout'  => 3,             // xato yoki sekin bo'lsa ham buyurtma jarayoni to'xtamaydi
        'blocking' => true,
        'headers'  => ['Content-Type' => 'application/json', 'X-Timestamp' => $ts, 'X-Signature' => $sig],
        'body'     => $payload,
    ]);
    if (!is_wp_error($res) && wp_remote_retrieve_response_code($res) < 300) {
        $order->update_meta_data('_vd_sent', 1);
        $order->save();
    }
}
add_action('woocommerce_order_status_processing', 'vd_send_order');
add_action('woocommerce_order_status_completed', 'vd_send_order');
add_action('woocommerce_payment_complete', 'vd_send_order');
