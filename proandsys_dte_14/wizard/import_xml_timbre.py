# -*- coding: utf-8 -*-


from odoo import models, fields, api, exceptions
import base64
#from tempfile import TemporaryFile
import tempfile


class ImportXmlTimbreDte(models.TransientModel):
    _name = 'import.xml.timbre.dte'

    file = fields.Binary('Archivo XML')

    def import_xml(self):
        reg = None
        code = None
        caf_cond = False
        pub_cond = False
        priv_cond = False
        fileobj = tempfile.TemporaryFile()
        context = self._context

        vals = {
            'caf': '',
            'xml': None,
            'active': True,
            'end_folio': 0,
            'begin_folio': 0,
            'next_value': 0,
            'file_code': None,
            'public_key': '',
            'private_key': ''
        }
        
        wizard = self

        if 'active_model' and 'active_id' in context:
            reg = self.env[context['active_model']].browse(context['active_id'])
        else:
            raise exceptions.Warning('No se puede saber para cual diario está importando el registro, contacte con un administrador de sistema.')
        try:
            vals['xml'] = (base64.decodestring(wizard.file)).decode('iso-8859-1')
            vals['file'] = (wizard.file).decode('utf-8')
            fileobj.write(vals['xml'].encode('iso-8859-1'))
            fileobj.seek(0)

            for line in fileobj.readlines():
                if b'<CAF' in line:
                    caf_cond = True
                elif b'<RSASK>' in line:
                    priv_cond = True
                elif b'<RSAPUBK>' in line:
                    pub_cond = True

                if caf_cond:
                    vals['caf'] += line.decode('iso-8859-1')
                    if line.startswith(b'<TD>'):
                        vals['file_code'] = line.replace(b'<TD>',b'').replace(b'</TD>',b'').replace(b'\n',b'').replace(b'\r',b'')
                        if vals['file_code'].decode('ascii') != reg.type_id.code:
                            raise exceptions.Warning(\
                                'El codigo del tipo de documento del diario es distinto al entregado en '+\
                                'el archivo por el SII, favor revisar que el diario al que se estan importando '+\
                                'los Folios sea el correcto.' + vals['file_code'].decode('ascii') + '-' + reg.type_id.code)
                    if line.startswith(b'<RNG>'):
                        vals['begin_folio'] = line.split(b'</D><H>')[0].replace(b'<RNG><D>',b'').decode('ascii')
                        vals['end_folio'] = line.split(b'</D><H>')[1].replace(b'</H></RNG>',b'').decode('ascii')
                        vals['next_value'] = line.split(b'</D><H>')[0].replace(b'<RNG><D>',b'').decode('ascii')
                    if b'</CAF>' in line:
                        caf_cond = False
                if priv_cond:
                    if b'</RSASK>' in line:
                        priv_cond = False
                    else:
                        vals['private_key'] += line.replace(b'<RSASK>',b'').decode('ascii')
                if pub_cond:
                    if b'</RSAPUBK>' in line:
                        pub_cond = False
                    else:
                        vals['public_key'] += line.replace(b'<RSAPUBK>',b'').decode('ascii')
        finally:
            fileobj.close()

        reg.write(vals)
        seq_obj = self.env['ir.sequence']
        seq_dic = {}
        seq_dic['name'] = reg.type_id.display_name+'-'+reg.company_id.name
        seq_dic['prefix'] = reg.type_id.code
        seq_dic['number_next_actual'] = reg.begin_folio
        sequence = seq_obj.create(seq_dic)
        reg.sequence_id = sequence.id
        return True
