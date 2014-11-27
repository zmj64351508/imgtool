#!/bin/sh

#examples
#./replace_kernel.sh 8192
#./replace_kernel.sh 8192 ~/work/elite-project

echo "You can specify page size and kernel path."
echo "examples: ./replace_kernel.sh 8192 ~/work/elite-project"
echo ""

#set default page_size and kernel_path
page_size=4096
kernel_path=/home/magee/Work/repository/elite-project

if [ $# -eq 1 ] ; then
	page_size=$1
elif [ $# -eq 2 ] ; then
	page_size=$1
	kernel_path=$2
fi

echo "Page size is: ${page_size}"
echo "Kernel path is ${kernel_path}"

#split linux kernel and ramdisk:  boot.img-kernel  boot.img-ramdisk.gz
split_bootimg.pl boot.img

#gunzip the ramdisk:  boot.img-ramdisk.gz -- >> boot.img-ramdisk
rm -f boot.img-ramdisk
gunzip boot.img-ramdisk.gz

#extract files from boot.img-ramdisk archive to directory ramdisk
mkdir -p ramdisk
cd ramdisk
cpio -iF ../boot.img-ramdisk
cd ..

#prepare our kernel image: zImage
cp ${kernel_path}/arch/arm/boot/zImage .

#generate new ramdisk
./mkbootfs ramdisk | gzip > ramdisk-new.gz

#cp ramdisk-new.gz ./boot.img-ramdisk.gz 
./mkbootimg --kernel zImage --ramdisk ramdisk-new.gz --cmdline "console=ttyS1,115200n8" --base 0x02008000 --pagesize ${page_size} -o newboot.img

#add sign
./signx64 -t uboot -i newboot.img

mv uboot_toc_image.bin signboot.img

#clean temp file and dir
rm -rf boot.img-ramdisk ramdisk zImage boot.img-kernel ramdisk-new.gz
