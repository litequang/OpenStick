<?php
// Integration configuration only. Upstream code and its MIT license are unchanged.
$root = $_SERVER['HTTP_X_OPENSTICK_ROOT'] ?? '';
$site = $_SERVER['HTTP_X_OPENSTICK_SITE'] ?? '';
if (!preg_match('/^(main|[0-9a-f-]{36}|sandbox)$/D', $site)
    || !(($site === 'main' && $root === '/var/www/openstick')
      || ($site === 'sandbox' && $root === '/var/lib/openstick-filegator/sandbox')
      || ($root === '/var/www/openstick-sites/'.$site && $site !== 'main' && $site !== 'sandbox'))
    || realpath($root) !== $root || is_link($root)) {
    http_response_code(403); exit;
}
$private = '/var/lib/openstick-filegator';
$work = $private.'/work/'.$site;
if (!is_dir($work)) { mkdir($work, 0700, true); }
ini_set('open_basedir', __DIR__.':'.$private.':'.$root.':/usr/share/php83');
$config = require __DIR__.'/configuration_sample.php';
$config['timezone'] = 'Asia/Ho_Chi_Minh';
$config['overwrite_on_upload'] = false;
$config['download_inline'] = ['pdf'];
$config['frontend_config']['app_name'] = 'OpenStick — FileGator';
$config['frontend_config']['logo'] = '';
$config['frontend_config']['upload_max_size'] = 128 * 1024 * 1024;
$config['frontend_config']['upload_chunk_size'] = 1024 * 1024;
$config['frontend_config']['upload_simultaneous'] = 1;
$config['frontend_config']['search_simultaneous'] = 1;
$config['frontend_config']['editable'] = ['.txt', '.css', '.js', '.html', '.htm', '.json', '.md', '.xml'];
$config['services']['Filegator\Services\Logger\LoggerInterface']['config']['monolog_handlers'] = [
    function () { return new \Monolog\Handler\NullHandler(); },
];
$config['services']['Filegator\Services\Session\SessionStorageInterface']['config']['handler'] =
    function () use ($work, $site) {
        return new \Symfony\Component\HttpFoundation\Session\Storage\NativeSessionStorage([
            'cookie_path' => '/files/'.$site.'/', 'cookie_samesite' => 'Strict',
            'cookie_httponly' => true, 'cookie_secure' => false,
        ], new \Symfony\Component\HttpFoundation\Session\Storage\Handler\NativeFileSessionHandler($work));
    };
$config['services']['Filegator\Services\Tmpfs\TmpfsInterface']['config']['path'] = $work.'/';
$config['services']['Filegator\Services\Security\Security']['config']['csrf_key'] =
    trim(file_get_contents($private.'/csrf-key'));
$config['services']['Filegator\Services\Storage\Filesystem']['config']['adapter'] =
    function () use ($root) { return new \League\Flysystem\Adapter\Local($root); };
$config['services']['Filegator\Services\Auth\AuthInterface']['config']['file'] = $private.'/users.json';
$config['services']['Filegator\Services\View\ViewInterface']['config']['add_to_head'] =
    '<meta name="referrer" content="same-origin"><style>.navbar-item.login{display:none!important}</style>';
$config['services']['Filegator\Services\View\ViewInterface']['config']['add_to_body'] =
    '<a href="/website" style="position:fixed;right:12px;bottom:12px;z-index:40;background:#164e63;color:white;padding:10px 16px;border-radius:24px">← Website</a>';
return $config;
