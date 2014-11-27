#! /bin/bash
kernel=~/Work/repository/elite-project
echo -e "\033[0;32mUsing kernel: $kernel\033[0m"
rm -rf .tmp
./unpack_ramdisk.sh $1 .tmp
mv .tmp/zImage .tmp/zImage.old
cp $kernel/arch/arm/boot/zImage .tmp/zImage

newimg=`basename $1`

./pack_ramdisk.sh .tmp $newimg-new
mv .tmp/$newimg-new .
rm -rf .tmp
