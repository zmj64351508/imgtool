#!/usr/bin/python
import os
import sys, getopt
import shutil
import argparse

class UsageError(Exception):
	def __init__(self):
		pass

def run_cmd(cmd):
    #global quiet
    #if not quiet:
	print cmd
	os.system(cmd)

def get_script_name():
	return os.path.basename(sys.argv[0])
	
def print_usage():
	print "usage: " + get_script_name() + " image_type action [...]\n"
	print "  image_type     ramdisk/ext4/yaffs2"
	print "  action         pack/unpack/clean"

class Work(object):
	def __init__(self):
		self.utils_dir = self.get_utils_dir()
		self.argv_to_parse = None

	def mkoutput_dir(self, output_dir):
		self.clean_output(output_dir)
		os.makedirs(output_dir)
		return os.path.abspath(output_dir)

	def do_work(self, argc, argv):
		self.parse_args(argc, argv)
		self.set_default_params()
		self.set_params(self.argv_to_parse)
		self.do_work_initialized(argc, argv)

	def run_utils(self, cmd):
		run_cmd(self.utils_dir  + cmd)

	# default version of clean output
	def clean_output(self, output_dir):
		if os.path.exists(output_dir):
			shutil.rmtree(output_dir)

	# default check arguments
	def check_args(self, argc, argv, min_argc):
		if argc < min_argc:
			raise UsageError
		# no output specific
		if argc == min_argc or argv[min_argc][0] == "-":
			self.output = self.get_default_output()
			self.argv_to_parse = argv[min_argc:]
		else:
			self.output = argv[min_argc]
			self.argv_to_parse = argv[min_argc + 1:]
			
		# use argv[1] as output by default
		if not os.path.exists(argv[1]):
			raise OSError, argv[1] + " not existes"

	def get_utils_dir(self):
		path = os.path.realpath(sys.path[0])
		if os.path.isfile(path):
			path = os.path.dirname(path)
		return os.path.abspath(path) + "/utils/"

	# following methods should be implemented by child classes
	def set_params(self, argv_to_parse):
		pass

	def set_default_params(self):
		pass

	def parse_args(self, argc, argv):
		pass

	def do_work_initialized(self, argc, argv):
		pass

class PackWork(Work):
	# can be overrided by child classes
	def parse_args(self, argc, argv):
		self.check_args(argc, argv, 2)
		self.input_dir = argv[1]

class UnpackWork(Work):
	# can be overrided by child classes
	def parse_args(self, argc, argv):
		self.check_args(argc, argv, 2)
		self.img_abs_path = os.path.abspath(argv[1])
		self.img_name = os.path.basename(argv[1])

class ImageType(object):
	def __init__(self):
		self.unpack_work = None
		self.pack_work = None

	def start(self, argc, argv):
		try:
			if argc < 2:
				raise UsageError
			if argv[1] == "pack":
				self.pack_work.do_work(argc - 1, argv[1:])
			elif argv[1] == "unpack":
				self.unpack_work.do_work(argc - 1, argv[1:])
			elif argv[1] == "clean":
				if argc >= 3:
					self.unpack_work.clean_output(argv[2])
				else:
					self.unpack_work.clean_output(self.unpack_work.get_default_output())
			else:
				raise UsageError
		except UsageError:
			self.usage()
		except Exception, e:
			print e 

	# argc >= 1
	# argv is: pack argv[1] argv[2]...
	def usage(self):
		pass

class Ext(ImageType):
	def usage(self):
		print "usage:"
		print get_script_name() + " ext(4) unpack image_name [output_dir]"
		print get_script_name() + " ext(4) pack input_dir mount_point [image_name] [--size]"
		print "\t--size image_size"
		print get_script_name() + " ext(4) clean [output_dir]"

	def __init__(self):
		super(Ext, self).__init__()
		self.unpack_work = self.ExtUnpackWork()
		self.pack_work = self.ExtPackWork()

	class ExtUnpackWork(UnpackWork):
		def __init__(self):
			super(Ext.ExtUnpackWork, self).__init__()
			self.fs_name = "fs"

		def get_default_output(self):
			return "ext_unpacked"

		def clean_output(self, output_dir):
			# umount the ext_fs if needed
			extfs_path = os.path.join(output_dir, self.fs_name)
			if os.path.exists(extfs_path) and os.path.ismount(extfs_path):
				run_cmd("umount " + extfs_path)
			super(Ext.ExtUnpackWork, self).clean_output(output_dir)

		def do_work_initialized(self, argc, argv):
			start_dir = os.getcwd()

			# make output dir
			output_abs_path = self.mkoutput_dir(self.output)
			os.chdir(self.output)

			# $utils_dir/simg2img $1 $imgname-raw
			raw_img_name = self.img_name + "-raw"
			self.run_utils("simg2img " + self.img_abs_path + " " + raw_img_name)
			fs_abs_path = self.mkoutput_dir(self.fs_name);
			run_cmd("mount -o loop " + raw_img_name + " " + self.fs_name)

	class ExtPackWork(PackWork):
		def __init__(self):
			super(Ext.ExtPackWork, self).__init__()
			self.fs_name = "fs"

		def get_default_output(self):
			return "new_ext.img"

		def parse_args(self, argc, argv):
			self.check_args(argc, argv, 3)
			self.input_dir = argv[1]
			self.mount_point = argv[2]

		def set_default_params(self):
			# default parameters
			self.image_size = "512M"

		def set_params(self, argv_to_parse):
			# parse parameters by in comming arguments
			opts, args = getopt.getopt(argv_to_parse, "", ["size="])
			for op, value in opts:
				if op in ("--size"):
					self.image_size = value

		def do_work_initialized(self, argc, argv):
			#"make_ext4fs $ENABLE_SPARSE_IMAGE $FCOPT -l $SIZE -a $MOUNT_POINT $OUTPUT_FILE $SRC_DIR"
			self.run_utils("make_ext4fs -s " + 
				       "-l " + self.image_size + " " + 
				       "-a " + self.mount_point + " " +
				       os.path.join(self.input_dir, self.output) + " " +
				       os.path.join(self.input_dir, self.fs_name))

class Ramdisk(ImageType):
	def usage(self):
		print "usage:"
		print get_script_name() + " ramdisk unpack image_name [output_dir]"
		print get_script_name() + " ramdisk pack input_dir [image_name] [--cmdline --base --page_size]"
		print "\t--cmdline    cmdline arguments"
		print "\t--base       base address"
		print "\t--page_size  page_size"
		print get_script_name() + " ramdisk clean [output_dir]"

	def __init__(self):
		super(Ramdisk, self).__init__()
		self.unpack_work = self.RamdiskUnpackWork()
		self.pack_work = self.RamdiskPackWork()

	class RamdiskUnpackWork(UnpackWork):	
		def get_default_output(self):
			return "ramdisk_unpacked"

		def do_work_initialized(self, argc, argv):
			start_dir = os.getcwd()

			# make output dir
			output_abs_path = self.mkoutput_dir(self.output)
			os.chdir(self.output)

			# split boot.img to boot.img-ramdisk.gz and kernel
			self.run_utils("split_bootimg.pl " + self.img_abs_path)

			# extract boot.img-ramdisk.gz to boot.img-ramdisk
			run_cmd("gunzip " + self.img_name + "-ramdisk.gz")
			img_ramdisk_abs_path = os.path.abspath(self.img_name + "-ramdisk")
			img_kernel_abs_path = os.path.abspath(self.img_name + "-kernel")

			# extract files from boot.img-ramdisk to ramdisk
			os.makedirs("ramdisk")
			os.chdir("ramdisk")
			run_cmd("cpio -iF " + img_ramdisk_abs_path)

			# clean temp file and dir
			#rm -rf $imgname-ramdisk 
			#mv -f $imgname-kernel zImage
			os.remove(img_ramdisk_abs_path)
			os.rename(img_kernel_abs_path, os.path.dirname(img_kernel_abs_path) + "/zImage")

			os.chdir(start_dir)

	class RamdiskPackWork(PackWork):
		def get_default_output(self):
			return "new_ramdisk.img"

		def set_default_params(self):
			# default values
			self.cmdline = "console=ttyS1,115200n8 rootdelay=2 no_console_suspend selinux=0"
			self.base = "0x0200800"
			self.page_size = "4096"

		def set_params(self, argv_to_parse):
			# parse parameters by in comming arguments
			opts, args = getopt.getopt(argv_to_parse, "", ["base=", "page_size=", "cmdline="])
			for op, value in opts:
				if op in ("--base"):
					self.base = value
				elif op in ("--page_size"):
					self.page_size = value
				elif op in ("--cmdline"):
					self.cmdline = value

		def do_work_initialized(self, argc, argv):
			# mkbootfs $1/ramdisk | gzip > $1/ramdisk-new.gz
			self.run_utils("mkbootfs " + self.input_dir + "/ramdisk | " +
				       "gzip > " + self.input_dir + "/ramdisk-new.gz")
			#$utils_dir/mkbootimg --kernel $1/zImage --ramdisk $1/ramdisk-new.gz 
			# --cmdline "console=ttyS1,115200n8 rootdelay=2 no_console_suspend selinux=0" 
			# --base 0x02008000 --pagesize ${page_size} -o $1/$newimg
			self.run_utils("mkbootimg " +
					"--kernel " + os.path.join(self.input_dir, "zImage") + " " +
					"--ramdisk " + os.path.join(self.input_dir, "ramdisk-new.gz") + " " +
					"--cmdline \""  + self.cmdline  + "\" " + 
					"--base " + self.base + " " + 
					"--pagesize " + self.page_size + " " +
					"-o " + os.path.join(self.input_dir, self.output))
			os.remove(self.input_dir + "/ramdisk-new.gz")

class Yaffs(ImageType):
	def usage(self):
		print "usage:"
		print get_script_name() + " yaffs(2) unpack image_name [output_dir] [--page_size]"
		print "\t--page_size page_size"
		#print get_script_name() + " yaffs(2) pack input_dir"
		print get_script_name() + " yaffs(2) clean [output_dir]"

	def __init__(self):
		super(Yaffs, self).__init__()
		self.unpack_work = self.YaffsUnpackWork()
		#self.pack_work = self.YaffsPackWork()

	class YaffsUnpackWork(UnpackWork):
		def __init__(self):
			super(Yaffs.YaffsUnpackWork, self).__init__()
			self.fs_name = "fs"

		def get_default_output(self):
			return "yaffs_unpacked"

		def set_default_params(self):
			# default values
			self.page_size = "4096"

		def set_params(self, argv_to_parse):
			# parse parameters by in comming arguments
			opts, args = getopt.getopt(argv_to_parse, "", ["page_size="])
			for op, value in opts:
				if op in ("--page_size"):
					self.page_size = value

		def do_work_initialized(self, argc, argv):
			start_dir = os.getcwd()

			# make output dir
			output_abs_path = self.mkoutput_dir(self.output)
			os.chdir(self.output)

			self.run_utils("unyaffs2 " + self.img_abs_path + " " + self.page_size)
			os.rename("unpack", self.fs_name)
			os.chdir(start_dir)

class ImageTypeFactory(object):
	def __init__(self):
		self.images = { 
			"ramdisk":Ramdisk,
			"ext": Ext,
			"ext4": Ext,
			"yaffs": Yaffs,
			"yaffs2": Yaffs
		}
	
	def create(self, image_type):
		return self.images[image_type]()
		
def main(argc, argv):
	if argc < 2:
		raise UsageError

	image_factory = ImageTypeFactory()
	image_type = image_factory.create(argv[1])
	image_type.start(argc - 1, argv[1:])

image_type = None

if __name__ == "__main__":
	try:
		main(len(sys.argv), sys.argv)
	except UsageError:
		print_usage()

