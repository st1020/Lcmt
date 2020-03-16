#!/usr/bin/env python3
# A Linux Container Manager On Termux

import sys
import os
import re
import configparser
import argparse
import time
import hashlib
import tarfile
import requests
from prettytable import PrettyTable
from tqdm import tqdm

sys.setrecursionlimit(1000000)

lcmt_home = os.getenv('HOME') + '/.lcmt'
source_url = 'https://raw.githack.com/st1020/lcmt/master/source.conf'

def ListImage(args):
    if args.verbosity:
        for name in local_config.sections():
            args.name = name
            InfoImage(args)
    elif args.download:
        list = PrettyTable(['发行版', '版本' ,'类型' ,'可安装'])
        for name in source_config.sections():
            version = source_config[name]['version']
            type = source_config[name]['type']
            available = arch in source_config[name]
            list.add_row([name, version, type, available])
        print(list)
    else:
        for name in local_config.sections():
            print ('\n   名称：' + name)
            print ('\n\t描述：' + local_config[name]['description'])
            print ('\n\t大小：' + str(GetDirSizeByShell(local_config[name]['path'])))
            print ('\n\t创建时间：' + local_config[name]['date'])
            print ('\n\t路径：' + local_config[name]['path'])
            mount = ''
            for a in local_config.options(name):
                if 'mount' in a:
                    mount += local_config[name][a] + '\n\t\t'
            if not mount:
                mount = 'None'
            print ('\n\t挂载：' + mount)
    
def RemoveImage(args):
    if args.name in local_config:
        print('正在删除' + args.name + '中...')
        if not args.conf_only:
            os.system('chmod -R 777 ' + local_config[args.name]['path'])
            os.system('rm -rf ' + local_config[args.name]['path'])
        local_config.remove_section(args.name)
        with open(lcmt_home + '/local.conf', 'w') as configfile:
            local_config.write(configfile)
        print('删除完成！')
    else:
        print('您输入的镜像名称不存在')
        exit(1)
    
def AddImage(args):
    if args.name in local_config:
        print('您输入的镜像名称已存在')
        exit(1)
    if not args.path:
        args.path = lcmt_home + '/' + args.name
    args.path = os.path.abspath(os.path.expanduser(args.path))
    if not os.path.isdir(args.path):
        os.makedirs(args.path)
    if os.listdir(args.path):
        print('您输入的路径非空文件夹')
        exit(1)
    if not args.image:
        print('请输入要添加的镜像类型或路径')
        exit(1)
    if args.image in source_config:
        print('正在下载镜像...')
        d = DownloadImage(args.image)
        if os.path.isfile(d):
            print('正在解压镜像...')
            UnzipImage(d, args.path)
            if 'shell' in source_config[args.image] and not args.shell:
                args.shell = source_config[args.image]['shell']
        else:
            print(d)
            exit(1)
    elif os.path.isfile(args.image):
        print('正在解压镜像...')
        UnzipImage(args.image, args.path)
    else:
        print('您输入的--image参数错误')
        exit(1)
    if not args.shell:
        args.shell = '/bin/bash'
    if '/' not in args.shell:
        args.shell = '/bin/' + args.shell
    #set local_config
    print('正在配置镜像...')
    local_config.add_section(args.name)
    local_config.set(args.name, 'description', str(args.description))
    local_config.set(args.name, 'date', time.strftime("%Y-%m-%d",time.localtime(time.time())) + ' ' + time.strftime("%H:%M:%S",time.localtime(time.time())))
    local_config.set(args.name, 'path', str(args.path))
    local_config.set(args.name, 'work', str(args.work))
    local_config.set(args.name, 'shell', str(args.shell))
    if args.mount:
        i = 0
        for a in args.mount:
            i += 1
            local_config.set(args.name, 'mount_' + str(i), a)
    if args.env:
        i = 0
        for a in args.env:
            i += 1
            local_config.set(args.name, 'env_' + str(i), a)
    local_config.set(args.name, 'kill', str(args.kill_on_exit))
    local_config.set(args.name, 'root', str(args.no_root_id))
    with open(lcmt_home + '/local.conf', 'w') as configfile:
        local_config.write(configfile)
    print('镜像添加完成')
    
def ConfImage(args):
    if args.name in local_config:
        if args.description:
            local_config.set(args.name, 'description', args.description)
        if args.shell:
            if '/' not in args.shell:
                args.shell = '/bin/' + args.shell
            local_config.set(args.name, 'shell', args.shell)
        if args.work:
            local_config.set(args.name, 'work', args.work)
        if args.add_mount:
            i = 0
            for a in local_config.options(args.name):
                if 'mount' in a:
                    i += 1
            for a in args.add_mount:
                i += 1
                local_config.set(args.name, 'mount_' + str(i), a)
        if args.change_mount:
            for a in local_config.options(args.name):
                if 'mount' in a:
                    local_config.remove_option(args.name, a)
            i = 0
            for a in args.change_mount:
                i += 1
                local_config.set(args.name, 'mount_' + str(i), a)
        if args.add_env:
            i = 0
            for a in local_config.options(args.name):
                if 'env' in a:
                    i += 1
            for a in args.add_env:
                i += 1
                local_config.set(args.name, 'env_' + str(i), a)
        if args.change_env:
            for a in local_config.options(args.name):
                if 'env' in a:
                    local_config.remove_option(args.name, a)
            i = 0
            for a in args.change_env:
                i += 1
                local_config.set(args.name, 'env_' + str(i), a)
        if args.kill_on_exit:
            local_config.set(args.name, 'kill', 'True')
        if args.no_kill_on_exit:
            local_config.set(args.name, 'kill', 'False')
        if args.root_id:
            local_config.set(args.name, 'root', 'True')
        if args.no_root_id:
            local_config.set(args.name, 'root', 'False')
        with open(lcmt_home + '/local.conf', 'w') as configfile:
            local_config.write(configfile)
    else:
        print('此镜像不存在')
    
def RunImage(args):
    if args.name in local_config:
        if args.shell:
            if '/' not in args.shell:
                args.shell = '/bin/' + args.shell
            local_config[args.name]['shell'] = args.shell
        if args.mount:
            i = 0
            for a in local_config.options(name):
                if 'mount' in a:
                    i += 1
            for a in args.mount:
                i += 1
                local_config.set(args.name, 'mount_' + str(i), a)
        if args.env:
            i = 0
            for a in local_config.options(name):
                if 'env' in a:
                    i += 1
            for a in args.env:
                i += 1
                local_config.set(args.name, 'env_' + str(i), a)
        os.unsetenv('LD_PRELOAD')
        os.system(GetCommand(args.name))
    else:
        print('输入错误')
    
def InfoImage(args):
    if args.name in local_config:
        print ('\n   名称：' + args.name)
        print ('\n\t描述：' + local_config[args.name]['description'])
        print ('\n\t大小：' + str(GetDirSizeByShell(local_config[args.name]['path'])))
        print ('\n\t创建时间：' + local_config[args.name]['date'])
        print ('\n\t路径：' + local_config[args.name]['path'])
        print ('\n\tShell：' + local_config[args.name]['shell'])
        print ('\n\tKill On Exit：' + local_config[args.name]['kill'])
        print ('\n\tRoot Id：' + local_config[args.name]['root'])
        print ('\n\t工作目录：' + local_config[args.name]['work'])
        mount = ''
        for a in local_config.options(args.name):
            if 'mount' in a:
                mount += local_config[args.name][a] + '\n\t\t'
        if not mount:
            mount = 'None'
        print ('\n\t挂载：' + mount)
        env = ''
        for a in local_config.options(args.name):
            if 'env' in a:
                env += local_config[args.name][a] + '\n\t\t'
        if not env:
            env = 'None'
        print ('\n\t环境变量：' + env)
        print ('\n\t启动命令：' + GetCommand(args.name))
    else:
        print('输入错误')
    
def Update(args):
    if not args.source:
        if not Download(source_url, lcmt_home + '/source.conf'):
            print('更新下载数据文件失败')
    if not Download(source_url, lcmt_home + '/source.conf'):
        print('程序更新失败')
    print('更新完成')
    
def CleanTemp(args):
    for root, dirs, files in os.walk(lcmt_home + '/download', topdown=False):
        for name in files:
            os.remove(os.path.join(root, name))
        for name in dirs:
            os.rmdir(os.path.join(root, name))
    print('下载缓存删除完成')
    
def DownloadImage(name):
    if arch in source_config[name]:
        download_path = lcmt_home + '/download/' + name + '.tar.' + source_config[name]['zip']
        if os.path.isfile(download_path):
            print('下载文件已存在，跳过下载...')
            return download_path
        else:
            download_url = source_config[name][arch]
            if '$time' in download_url:
                r = requests.get(re.sub(r'(.*\/)\$time.*', r'\1', download_url))
                find = re.findall(r'title=".{8}_..:.."', r.text)
                i = 0
                for match in find:
                    find[i] = int(re.sub(r'title="(.{8})_(..):(..)"', r'\1\2\3', match))
                    i += 1
                download_url = download_url.replace('$time', re.sub(r'(.{8})(..)(..)', r'\1_\2:\3', str(max(find))))
            if Download(download_url, download_path):
                if source_config[name]['hash'] == 'no':
                    return download_path
                elif source_config[name]['hash'] == 'sha256':
                    check_path = download_path + '.sha256'
                    if Download(download_url + '.sha256', check_path):
                        hash = hashlib.sha256()
                    else:
                        return 'Get SHA256SUMS Failed'
                elif source_config[name]['hash'] == 'md5':
                    check_path = download_path + '.md5'
                    if Download(download_url + '.md5', check_path):
                        hash = hashlib.md5()
                    else:
                        return 'Get MD5SUMS Failed'
                elif source_config[name]['hash'] == 'SHA256SUMS':
                    check_path = download_path + '.sha256'
                    if Download(re.sub(r'(.*\/).*', r'\1', download_url) + 'SHA256SUMS', check_path):
                        hash = hashlib.sha256()
                    else:
                        return 'Get SHA256SUMS Failed'
                else:
                    return 'Can not get check info'
                with open(download_path, 'rb') as f, open(check_path, 'r') as cf:
                    hash.update(f.read())
                    if hash.hexdigest() in cf.read():
                        return download_path
                    else:
                        return 'Chech Failed'
            else:
                return 'Download Failed'
    else:
        return 'Unsupported Architecture'

def UnzipImage(file, path):
    #if tarfile.is_tarfile(file):
        #with tarfile.open(name=file, mode='r') as tar:
            #for f in tqdm(tar.getnames()):
                #tar.extract(f, path)
            #tar.extractall(path = path)
    os.system('proot --link2symlink tar -axpf ' + file + ' -C ' + path)
    #else:
        #print('压缩文件损坏')

def GetDirSizeByShell(doc_path):
    return os.popen(f'du -sh {doc_path}').read().split( )[0]

def Download(url, path):
    with requests.get(url, stream=True) as r:
        if not r.status_code == 200:
            return False
        else:
            total_size = int(r.headers.get('Content-Length'))
            with open(path, 'wb') as f, tqdm(total=total_size, unit_scale=True, unit_divisor=1024, unit='iB') as t:
                for data in r.iter_content(1024):
                    t.update(1024)
                    f.write(data)
            return True
    
def GetCommand(name):
    command = 'proot --link2symlink '
    if local_config[name].getboolean('root'):
        command += '-0 '
    if local_config[name].getboolean('kill'):
        command += '--kill-on-exit '
    command += '-r ' + local_config[name]['path']
    command += ' -b /sys -b /dev -b /proc'
    for a in local_config.options(name):
        if 'mount' in a:
            command += ' -b ' + local_config[name][a]
    command += ' -w ' + local_config[name]['work'] + ' /usr/bin/env -i'
    for a in local_config.options(name):
        if 'env' in a:
            command += ' ' + local_config[name][a]
    command += ' TERM=' + os.getenv('TERM')
    command += ' PATH=/bin:/usr/bin:/sbin:/usr/sbin:/usr/local/bin:/usr/local/sbin'
    command += ' HOME=' + local_config[name]['work']
    command += ' ' + local_config[name]['shell']
    command += ' --login'
    return command
	
if __name__ == '__main__':
    arch = os.uname().machine
    if arch == 'aarch64':
        pass
    elif arch == 'x86_64':
        arch = 'amd64'
    elif '86' in arch:
        arch = 'i386'
    elif 'arm' in arch:
        arch = 'armhf'
    else:
        print('您的设备架构不受支持，但这并不代表您无法使用本工具，您可以自行下载支持您的设备架构的Linux容器镜像')
    
    source_config = configparser.ConfigParser()
    local_config = configparser.ConfigParser()
    
    if not os.path.isdir(lcmt_home):
        os.mkdir(lcmt_home)
    if not os.path.isdir(lcmt_home + '/download'):
        os.mkdir(lcmt_home + '/download')
    if not os.path.isfile(lcmt_home + '/local.conf'):
        with open(lcmt_home + '/local.conf', 'w') as configfile:
            local_config.write(configfile)
    local_config.read(lcmt_home + '/local.conf')
    if not os.path.isfile(lcmt_home + '/source.conf'):
        if not Download(source_url, lcmt_home + '/source.conf'):
            print('下载数据文件下载失败')
        source_config.read(lcmt_home + '/source.conf')
    else:
        source_config.read(lcmt_home + '/source.conf')
    
    
    parser = argparse.ArgumentParser(prog = 'lcmt',
        description = 'A Linux Container Manager on Termux',
        epilog = 'Author:St1020')
    
    subparsers = parser.add_subparsers(title = '子选项',
        description = '请输入 lcmt {子选项} --help 获取更多帮助')
    
    
    parser_add = subparsers.add_parser('add',
        aliases = ['a'],
        help = '新建镜像')
    parser_add.add_argument('name',
        help = '镜像名称')
    parser_add.add_argument('-i', '--image',
        help = '选择要安装的镜像',
        metavar = '[debian|~/folder/debian.tar]')
    parser_add.add_argument('-d', '--description',
        help = '设置镜像的描述')
    parser_add.add_argument('-p', '--path',
        help = '设置镜像的存储路径')
    parser_add.add_argument('-w', '--work',
        help = '设置工作目录',
        metavar = '[/home]',
        default = '/root')
    parser_add.add_argument('-s', '--shell',
        help = '使用指定的Shell启动',
        metavar = '[/bin/bash]')
    parser_add.add_argument('-m', '--mount',
        help = '启动时挂载指定目录',
        nargs = '*',
        metavar = '~/folder|~/folder:/root/folder')
    parser_add.add_argument('-e', '--env',
        help = '启动时设置指定环境变量',
        nargs = '*',
        metavar = 'LANG = zh_CN.UTF-8')
    parser_add.add_argument('-k', '--kill-on-exit',
        help = '退出时结束所有进程',
        action = 'store_true',
        default = False)
    parser_add.add_argument('-n0', '--no-root-id',
        help = '不模拟Root权限账户',
        action = 'store_false',
        default = True)
    parser_add.set_defaults(func = AddImage)
    
    
    parser_remove = subparsers.add_parser('remove',
        aliases = ['r'],
        help = '删除镜像')
    parser_remove.add_argument('name',
        help = '镜像名称')
    parser_remove.add_argument('-c', '--conf-only',
        help = '仅删除镜像的配置信息而不删除镜像文件',
        action = 'store_true')
    parser_remove.set_defaults(func = RemoveImage)
    
    
    parser_list = subparsers.add_parser('list',
        aliases = ['l'],
        help = '列出所有镜像')
    parser_list.add_argument('-v', '--verbosity',
        help = '显示详细信息',
        action = 'store_true')
    parser_list.add_argument('-d', '--download',
        help = '列出可供下载的镜像',
        action = 'store_true')
    parser_list.set_defaults(func = ListImage)
    
    
    parser_edit = subparsers.add_parser('edit',
        aliases = ['e'],
        help = '编辑镜像信息')
    parser_edit.add_argument('name',
        help = '镜像名称')
    parser_edit.add_argument('-d', '--description',
        help = '设置镜像的描述')
    parser_edit.add_argument('-w', '--work',
        help = '设置工作目录',
        metavar = '[/home]')
    parser_edit.add_argument('-s', '--shell',
        help = '使用指定的Shell启动',
        metavar = '[/bin/bash]')
    parser_edit.add_argument('-am', '--add-mount',
        help = '添加启动时挂载的目录',
        nargs = '*',
        metavar = '~/folder|~/folder:/root/folder')
    parser_edit.add_argument('-cm', '--change-mount',
        help = '修改启动时挂载的目录',
        nargs = '*',
        metavar = '~/folder|~/folder:/root/folder')
    parser_edit.add_argument('-ae', '--add-env',
        help = '添加启动时设置的环境变量',
        nargs = '*',
        metavar = 'LANG = zh_CN.UTF-8')
    parser_edit.add_argument('-ce', '--change-env',
        help = '添加启动时设置的环境变量',
        nargs = '*',
        metavar = 'LANG = zh_CN.UTF-8')
    parser_edit.add_argument('-k', '--kill-on-exit',
        help = '退出时结束所有进程',
        action = 'store_true',
        default = False)
    parser_edit.add_argument('-nk', '--no-kill-on-exit',
        help = '退出时不结束所有进程',
        action = 'store_true',
        default = False)
    parser_edit.add_argument('-0', '--root-id',
        help = '模拟Root权限账户',
        action = 'store_true',
        default = False)
    parser_edit.add_argument('-n0', '--no-root-id',
        help = '不模拟Root权限账户',
        action = 'store_true',
        default = False)
    parser_edit.set_defaults(func = ConfImage)
    
    
    parser_start = subparsers.add_parser('start',
        aliases = ['s'],
        help = '启动镜像')
    parser_start.add_argument('name',
        help = '镜像名称')
    parser_start.add_argument('-s', '--shell',
        help = '使用指定的Shell启动',
        metavar = '[/bin/bash]')
    parser_start.add_argument('-m', '--mount',
        help = '启动时挂载指定目录（临时添加）',
        nargs = '*',
        metavar = '~/folder|~/folder:/root/folder')
    parser_start.add_argument('-e', '--env',
        help = '启动时设置指定环境变量（临时添加）',
        nargs = '*',
        metavar = 'LANG = zh_CN.UTF-8')
    parser_start.set_defaults(func = RunImage)
    
    
    parser_info = subparsers.add_parser('info',
        aliases = ['i'],
        help = '显示镜像信息')
    parser_info.add_argument('name',
        help = '镜像名称')
    parser_info.set_defaults(func = InfoImage)
    
    parser_update = subparsers.add_parser('update',
        aliases = ['u'],
        help = '更新本程序和下载数据文件')
    parser_update.add_argument('-s', '--source',
        help = '仅更新下载数据文件',
        action = 'store_true',
        default = False)
    parser_update.set_defaults(func = Update)
    
    
    parser_clean = subparsers.add_parser('clean',
        aliases = ['c'],
        help = '删除下载缓存')
    parser_clean.set_defaults(func = CleanTemp)
    
    args = parser.parse_args()
    args.func(args)
