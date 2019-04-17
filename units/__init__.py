# -*- coding: utf-8 -*-
# @Author: John Hammond
# @Date:   2019-02-28 22:33:18
# @Last Modified by:   John Hammond
# @Last Modified time: 2019-04-16 22:23:32
from unit import BaseUnit
from pwn import *
import os
import magic
import traceback
import string
import enchant
import re

dictionary = enchant.Dict()
english_words_threshold = 1

BASE64_PATTERN = re.compile( '^[a-zA-Z0-9+/]+={0,2}$', flags= re.DOTALL | re.IGNORECASE  )


class NotApplicable(Exception):
	pass

class DependancyError(Exception):
	def __init__(self, dep):
		self.dependancy = dep

class FileOrDataUnit(BaseUnit):
	
	def __init__(self, katana, parent, target):

		# Assume that if the target opens properly as a file, that it is 
		# meant to be a file
		try:
			target = open(target, 'rb').read().decode('latin-1')
		except IsADirectoryError:
			raise NotApplicable # JOHN: This triggers too oftem on artifacts... 
		except (FileNotFoundError, ValueError,OSError):
			pass
		except:
			traceback.print_exc()

		# We do that before super, so that self.target always refers to
		# the correct target
		super(FileOrDataUnit, self).__init__(katana, parent, target)
	
class FileUnit(BaseUnit):
	
	def __init__(self, katana, parent, target, keywords=[]):
		super(FileUnit, self).__init__(katana, parent, target)
		
		# Ensure it's a file, and get it's mime type
		try:
			t = magic.from_file(target).lower()
		except IsADirectoryError:
			raise NotApplicable # JOHN: This triggers too oftem on artifacts... 
		except (FileNotFoundError, ValueError, OSError):
			raise NotApplicable()

		self.mime_type = t
		
		# Check for the keywords
		n = 0
		for kw in keywords:
			if kw not in t:
				n += 1

		# If no keywords were found, it doesn't match
		if n == len(keywords) and n != 0:
			raise NotApplicable()

		if ' image ' in t:
			# katana.add_image(self, os.path.abspath(target))
			katana.add_image(os.path.abspath(target)) # JOHN: I'm still unsure about putting all the images in every unit

class PrintableDataUnit(BaseUnit):
	
	def __init__(self, katana, parent, target):
	
		# Similar to FileOrDataUnit, use file if it exists
		try:
			target = open(target, 'rb').read().decode('latin-1')
		except IsADirectoryError:
			raise NotApplicable # JOHN: This triggers too oftem on artifacts... 
		except (FileNotFoundError, ValueError, OSError):
			pass
		except:
			traceback.print_exc()

		super(PrintableDataUnit, self).__init__(katana, parent, target)

		# If this is a bytes object, attempt to decode it as utf-8
		if type(self.target) is bytes:
			try:
				self.target = self.target.decode('utf-8')
			except UnicodeError:
				raise NotApplicable()
		
		# Ensure the string is printable
		for c in self.target:
			if c not in string.printable:
				raise NotApplicable()

class ContainsLettersUnit(BaseUnit):
	
	def __init__(self, katana, parent, target):
	
		# Similar to FileOrDataUnit, use file if it exists
		try:
			target = open(target, 'rb').read().decode('latin-1')
		except IsADirectoryError:
			raise NotApplicable # JOHN: This triggers too oftem on artifacts... 
		except (FileNotFoundError, ValueError, OSError):
			pass
		except:
			traceback.print_exc()

		super(ContainsLettersUnit, self).__init__(katana, parent, target)

		# If this is a bytes object, attempt to decode it as utf-8
		if type(self.target) is bytes:
			try:
				self.target = self.target.decode('utf-8')
			except UnicodeError:
				raise NotApplicable()
		
		# Ensure the string is printable
		for c in self.target:
			if c not in string.printable:
				raise NotApplicable()

		# DO NOT run this if the string does not contain any letters.
		odd_characters = 0
		for c in target:
			if c not in string.ascii_letters:
				odd_characters += 1

		if odd_characters == len(target):
			raise NotApplicable

class NotEnglishUnit(BaseUnit):
	
	def __init__(self, katana, parent, target):
	
		# Similar to FileOrDataUnit, use file if it exists
		try:
			target = open(target, 'rb').read().decode('latin-1')
		except IsADirectoryError:
			raise NotApplicable # JOHN: This triggers too oftem on artifacts... 
		except (FileNotFoundError, ValueError, OSError):
			pass
		except:
			traceback.print_exc()

		super(NotEnglishUnit, self).__init__(katana, parent, target)

		# If this is a bytes object, attempt to decode it as utf-8
		if type(self.target) is bytes:
			try:
				self.target = self.target.decode('utf-8')
			except UnicodeError:
				raise NotApplicable()
		
		# Ensure the string is printable
		for c in self.target:
			if c not in string.printable:
				raise NotApplicable()

		# Also ensure this isn't Base64 (a lot of false positives...)
		base64_result = BASE64_PATTERN.findall(str(self.target))
		if base64_result is not None and base64_result != []:
			raise NotApplicable()

		# Filter out words that are only two letters long...
		all_words = list(filter(lambda word : len(word)>2, re.findall('[A-Za-z]+', self.target)))
		english_words = list(filter(lambda word : len(word)>2, [ word for word in all_words if dictionary.check(word) ]))

		# This has a majority of English letters... it might be English!!
		# print('='*30)
		# print(target, all_words, english_words)
		if len(english_words) >= (len(all_words) - english_words_threshold) and len(english_words) != 0:
			# print("LOOKS LIKE ENGLISH")
			raise NotApplicable()
		# else:
		# 	print("NOT ENGLISH")

class BruteforcePasswordUnit(object):

	@classmethod
	def add_arguments(cls, katana, parser):
		parser.add_argument('--{0}-password'.format(cls.BRUTEFORCE_NAME), type=str,
			action='append', help='a password for {0} files'.format(cls.BRUTEFORCE_NAME),
			default=[]
		)
		return
	
	def enumerate(self, katana):
		# Default case of no password
		yield ''

		# Check each given password
		for p in katana.config['{0}_password'.format(self.BRUTEFORCE_NAME)]:
			yield p

		# Add all passwords from the dictionary file
		if 'dict' in katana.config and katana.config['dict'] is not None:
			katana.config['dict'].seek(0)
			for line in katana.config['dict']:
				yield line.rstrip('\n')
