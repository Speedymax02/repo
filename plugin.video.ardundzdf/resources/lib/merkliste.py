# -*- coding: utf-8 -*-
################################################################################
#				merkliste.py - Teil von Kodi-Addon-ARDundZDF
#			 Hinzufügen + Löschen von Einträgen der Merkliste
#	aus Haupt-PRG hierher verlagert, da sonst kein Verbleib im akt. Listing
#	möglich.
#	Listing der Einträge weiter in ShowFavs (Haupt-PRG)
################################################################################
#	Stand: 16.04.2020

from __future__ import absolute_import

from kodi_six import xbmc, xbmcaddon, xbmcplugin, xbmcgui, xbmcvfs
# o. Auswirkung auf die unicode-Strings in PYTHON3:
from kodi_six.utils import py2_encode, py2_decode

import base64 			# url-Kodierung für Kontextmenüs
import os, sys, subprocess 
import re				
import json		
PYTHON2 = sys.version_info.major == 2
PYTHON3 = sys.version_info.major == 3
if PYTHON2:
	from urllib import quote, unquote, quote_plus, unquote_plus
	from urlparse import parse_qs
elif PYTHON3:
	from urllib.parse import quote, unquote, quote_plus, unquote_plus, parse_qs

from util import PLog, stringextract, ReadFavourites, RSave, R, check_AddonXml

ADDON_ID      	= 'plugin.video.ardundzdf'
SETTINGS 		= xbmcaddon.Addon(id=ADDON_ID)
ADDON_PATH    	= SETTINGS.getAddonInfo('path')
ADDON_NAME    	= SETTINGS.getAddonInfo('name')
USERDATA		= xbmc.translatePath("special://userdata")
ADDON_DATA		= os.path.join("%sardundzdf_data") % USERDATA

if 	check_AddonXml('"xbmc.python" version="3.0.0"'):
	ADDON_DATA	= os.path.join("%s", "%s", "%s") % (USERDATA, "addon_data", ADDON_ID)
WATCHFILE		= os.path.join("%s/merkliste.xml") % ADDON_DATA

ICON 			= 'icon.png'		# ARD + ZDF
ICON_DIR_WATCH	= "Dir-watch.png"
PLog('Script merkliste.py geladen')

# ----------------------------------------------------------------------
# 02.04.2020 erweitert für Share-Zugriffe - hier Schreiben via 
#	xbmcvfs.File (für Python3 mittels Bytearray).
#	Lesen der Merkliste in ReadFavourites (Modul util).
#			
def Watch(action, name, thumb='', Plot='', url=''):		
	PLog('Watch: ' + action)

	# CallFunctions: Funktionen, die Videos direkt oder indirekt (isPlayable) aufrufen.
	#	Ist eine der Funktionen in der Plugin-Url enthalten, wird der Parameter Merk='true'
	#	für PlayVideo bzw. zum Durchreichen angehängt.
	#	Funktioniert nicht mit Modul funk
	CallFunctions = ["PlayVideo", "ZDF_getVideoSources", "resources.lib.zdfmobile.ShowVideo",
						"resources.lib.zdfmobile.PlayVideo", "SingleSendung", "ARDStartVideoStreams", 
						"ARDStartVideoMP4", "SenderLiveResolution", "resources.lib.phoenix.SingleBeitrag"
					]
	
	url = unquote_plus(url)	
	PLog(unquote_plus(url)[100:])  			# url in fparams zusätzlich quotiert
	PLog(name); PLog(thumb); PLog(Plot);
	
	item_cnt = 0; 
	err_msg	= ''
	doppler = False

	fname = WATCHFILE		
	if SETTINGS.getSetting('pref_merkextern') == 'true':	# externe Merkliste gewählt?
		fname = SETTINGS.getSetting('pref_MerkDest_path')
		if fname == '' or xbmcvfs.exists(fname) == False:
			PLog("merkextern: %s, %d" % (fname, xbmcvfs.exists(fname)))
			msg1 = u"Merkliste nicht gefunden"
			err_msg = u"Bitte Settings überprüfen"
			return msg1, err_msg, str(item_cnt)	
	
	if action == 'add':
		# Base64-Kodierung wird nicht mehr verwendet (addDir in Modul util), Code verbleibt 
		#	hier bis auf Weiteres
		if 'plugin://plugin' not in url:				# Base64-kodierte Plugin-Url in ActivateWindow
			b64_clean= convBase64(url)					# Dekodierung mit oder ohne padding am Ende	
			b64_clean=unquote_plus(b64_clean)			# unquote aus addDir-Call
			b64_clean=unquote_plus(b64_clean)			# unquote aus Kontextmenü
			#PLog(b64_clean)
			CallFunction = stringextract("&dirID=", "&", b64_clean) 
			PLog('CallFunction: ' + CallFunction)
			if CallFunction in CallFunctions:			# Parameter Merk='true' anhängen
				new_url = b64_clean[:-1]				# cut } am Ende fparams
				new_url = "%s, 'Merk': 'true'}" % new_url
				PLog("CallFunction_new_url: " + new_url)
				url = quote_plus(new_url)
				url = base64.b64encode(url)			
			
		url = url.replace('&', '&amp;') # Anpassung an Favorit-Schema
		merk = '<merk name="%s" thumb="%s" Plot="%s">ActivateWindow(10025,&quot;%s&quot;,return)</merk>'  \
			% (name, thumb, Plot, url)
		PLog('merk: ' + merk)
		my_items = ReadFavourites('Merk')				# 'utf-8'-Decoding in ReadFavourites
		merkliste = ''
		if len(my_items):
			PLog('my_items: ' + my_items[0])			# 1. Eintrag
			for item in my_items:						# Liste -> String
				iname = stringextract('name="', '"', item) 
				PLog('Name: %s, IName: %s' % (py2_decode(name), py2_decode(iname)))
				if py2_decode(iname) == py2_decode(name):# Doppler vermeiden
					doppler = True
					PLog('Doppler')
					break
				merkliste = merkliste + item + "\n"
				item_cnt = item_cnt + 1
		else:	
			pass
		
		item_cnt = item_cnt + 1		
		if doppler == False:
			msg1 = u"Eintrag hinzugefügt" 
			PLog(type(merkliste)); PLog(type(merk));
			merkliste = py2_decode(merkliste) + merk + "\n"
			#item_cnt = item_cnt + 1			
			merkliste = "<merkliste>\n%s</merkliste>"	% merkliste
			try:
				if '//' not in fname:
					err_msg = RSave(fname, merkliste, withcodec=True)	# Merkliste speichern
				else:
					PLog("xbmcvfs_fname: " + fname)
					f = xbmcvfs.File(fname, 'w')						# extern - Share		
					if PYTHON2:
						f = xbmcvfs.File(fname, 'w')
						ret=f.write(merkliste); f.close()			
					else:												# Python3: Bytearray
						buf = bytearray()
						buf.extend(merkliste.encode())
						ret=f.write(buf); f.close()			
					PLog("xbmcvfs_ret: " + str(ret))
					if ret:
						sync_list_intern(src_file=fname, dest_file=WATCHFILE)# Synchronisation
			except Exception as exception:
				PLog(str(exception))
				msg1 = u"Problem Merkliste"
				err_msg = str(exception)
				return msg1, err_msg, str(item_cnt)		
		else:
			msg1 = u"Eintrag schon vorhanden"
							 
	if action == 'del':
		my_items = ReadFavourites('Merk')			# 'utf-8'-Decoding in ReadFavourites
		if len(my_items):
			PLog('my_items: ' + my_items[-1])
		PLog(type(name));
		merkliste = ''
		deleted = False
		for item in my_items:						# Liste -> String
			iname = stringextract('name="', '"', item) # unicode
			iname = py2_decode(iname)
			name = py2_decode(name)		
			PLog('Name: %s, IName: %s' % (name, iname))		
			if name == iname:
				deleted = True						# skip Satz = löschen 
				continue
			item_cnt = item_cnt + 1
			merkliste = py2_decode(merkliste) + py2_decode(item) + "\n"
		if deleted:
			try:
				msg1 = u"Eintrag gelöscht"
				if '//' not in fname:
					err_msg = RSave(fname, merkliste, withcodec=True)	# Merkliste speichern
					PLog(msg1)
					if err_msg:
						ret = False
					else:
						ret = True
				else:
					PLog("xbmcvfs_fname: " + fname)
					f = xbmcvfs.File(fname, 'w')						# extern - Share		
					ret = f.write(merkliste); f.close()			
					PLog("xbmcvfs_ret: " + str(ret))
				if ret:
					sync_list_intern(src_file=fname, dest_file=WATCHFILE)# Synchronisation

			except Exception as exception:
				PLog(str(exception))
				msg1 = u"Problem Merkliste"
				err_msg = str(exception)
				return msg1, err_msg, str(item_cnt)	
		else:
			msg1 = "Eintrag nicht gefunden." 
			err_msg = u"Merkliste unverändert."
			PLog(msg1)	
							
	return msg1, err_msg, str(item_cnt)	

# ----------------------------------------------------------------------
# synchronisiert die interne Merkliste durch Überschreiben mit der
#	der externen Merkliste - Abbruch bei Abwahl von Synchronisieren 
#	oder externer Merkliste.
#
def sync_list_intern(src_file, dest_file):
	PLog('sync_list_intern:')
	
	# Vorprüfung Setting Sync / externe Merkliste
	if SETTINGS.getSetting('pref_merksync') == 'false' or SETTINGS.getSetting('pref_merkextern') == 'false':	
		PLog("Sync_OFF")
		return
	
	f = xbmcvfs.File(src_file)
	s1 = f.size(); f.close()
	if s1 > 100:							# Mindestbreite bis dirID=, Eintrag immer größer
		ret1 = xbmcvfs.delete(dest_file)
		PLog('xbmcvfs.delete: ' + str(ret1))
		ret2 = xbmcvfs.copy(src_file, dest_file)
		PLog('xbmcvfs.copy: ' + str(ret2))
		f = xbmcvfs.File(dest_file)
		s2 = f.size(); f.close()			# Größenvergleich
		PLog("s1: %d, s2: %d" % (s1, s2))
		
	
	if ret1 and ret2 and s2 == s1:
		PLog("Sync_OK")
	else:
		PLog("Sync_Error")
	return
	
# ----------------------------------------------------------------------			
# argv-Verarbeitung wie in router (Haupt-PRG)
# Beim Menü Favoriten (add) endet json.loads in exception

PLog(str(sys.argv))
PLog(sys.argv[2])
paramstring = unquote_plus(sys.argv[2])
# PLog('params: ' + paramstring)
params = dict(parse_qs(paramstring[1:]))
PLog('params_dict: ' + str(params))

PLog('action: ' + params['action'][0]) # hier immer action="dirList"
PLog('dirID: ' + params['dirID'][0])
# PLog('fparams: ' + params['fparams'][0])

func_pars = params['fparams'][0]
PLog("func_pars: " + func_pars)
name = stringextract("'name': ", ',', func_pars)	# für exceptions s.u.
name = name.replace("'", "")

try:
	func_pars = func_pars.replace("'", "\"")		# json.loads-kompatible string-Rahmen
	func_pars = func_pars.replace('\\', '\\\\')		# json.loads-kompatible Windows-Pfade
	mydict = json.loads(func_pars)
except Exception as exception:						# Bsp. Hinzufügen von Favoriten
	err_msg = str(exception)
	msg3=''
	if name:
		msg3 = "Eintrag >%s<" % name
	msg1 = "dieser Eintrag kann nicht verarbeitet werden."
	msg2 = "Fehler: %s" % err_msg
	MyDialog(msg1, msg2, msg3)
	exit()
	

action = mydict['action']	# action + name immmer vorh., Rest fehlt bei action=del
name = mydict['name']
thumb=''; Plot=''; url=''
if 'thumb' in mydict:		# thumb, Plot, url fehlen bei action del (s. addDir)
	thumb = mydict['thumb']
if 'Plot' in mydict:
	Plot = mydict['Plot']
if 'url' in mydict:
	url = mydict['url']
PLog(action); PLog(name); PLog(thumb); PLog(Plot); PLog(url); 

msg1, err_msg, item_cnt = Watch(action,name,thumb,Plot,url)

msg2 = err_msg
if item_cnt:
	msg2 = "%s\n%s" % (msg2, u"Einträge: %s" % item_cnt)
	if action == 'del':								# Refresh Liste nach Löschen
		xbmc.executebuiltin('Container.Refresh')
		
# 01.02.2029 Dialog ersetzt durch notification 
icon = R(ICON_DIR_WATCH)
xbmcgui.Dialog().notification(msg1,msg2,icon,5000)
# exit()		# thread.lock-Error in Kodi-Matrix

