# -*- coding: utf-8 -*-

from PyQt4.QtCore import *
from PyQt4.QtGui import *

from DlgAbout_ui import Ui_DlgAbout
import platform
import os
import codecs
import ConfigParser

try:
    import resources
except ImportError:
    import resources_rc

class DlgAbout(QDialog, Ui_DlgAbout):

    def __init__(self, parent=None):
        QDialog.__init__(self, parent)
        self.setupUi(self)
        cp = ConfigParser.ConfigParser()
        metadataFile = os.path.dirname(__file__) + os.sep + 'metadata.txt'
        cp.readfp(codecs.open(metadataFile, "r", "utf8"))
        name = cp.get('general', 'name')
        description = cp.get('general', 'description')
        version = cp.get('general', 'version')

        self.logo.setPixmap( QPixmap( ":/faunalia/logo" ) )
        self.title.setText( name )
        self.description.setText( description )

        text = self.txt.toHtml()
        text = text.replace( "$PLUGIN_NAME$", name )

        subject = "Help: %s" % name
        body = """\n\n
--------
Plugin name: %s
Plugin version: %s
Python version: %s
Platform: %s - %s
--------
""" % ( name, version, platform.python_version(), platform.system(), platform.version() )

        mail = QUrl( "mailto:abc@abc.com" )
        mail.addQueryItem( "subject", subject )
        mail.addQueryItem( "body", body )

        text = text.replace( "$MAIL_SUBJECT$", unicode(mail.encodedQueryItemValue( "subject" )) )
        text = text.replace( "$MAIL_BODY$", unicode(mail.encodedQueryItemValue( "body" )) )

        self.txt.setHtml(text)



