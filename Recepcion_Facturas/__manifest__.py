{
    'name': 'Recepción de Facturas',
    'version': '1.0',
    'author': 'www.fabricadeinnovacion.com',
    'category': 'Accounting',
    'summary': 'Procesar archivos adjuntos y crear facturas de compra.',
    'depends': ['base', 'mail', 'account'],
    'license': 'LGPL-3',
    'data': [
        'views/x_recepcion_facturas_views.xml',
    ],
    'installable': True,
    'application': False,
}
