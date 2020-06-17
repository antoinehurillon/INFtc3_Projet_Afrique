# -*- coding: utf-8 -*-
"""
Created on Wed May 27 09:25:27 2020

@author: antoi
"""

# Projet Afrique/Serveur_Afrique.py
# Partie serveur par Antoine HURILLON


import http.server
import socketserver
from urllib.parse import urlparse, parse_qs, unquote
import json
import sqlite3

# définition du handler
class RequestHandler(http.server.SimpleHTTPRequestHandler):

  # sous-répertoire racine des documents statiques
  static_dir = '/client'

  # version du serveur
  server_version = 'Serveur_Afrique.py/0.1'

  # on surcharge la méthode qui traite les requêtes GET
  def do_GET(self):
    self.init_params()

    # requete location - retourne la liste des pays et leurs coordonnées géogrpahiques
    if self.path_info[0] == "location":
      data=self.data_map()
      self.send_json(data)

    # requete description - retourne la description du pays dont on passe le nom en paramètre dans l'URL
    elif self.path_info[0] == "description":
      data=self.get_description(self.path_info[1])
      self.send_json(data)

    # requête générique
    elif self.path_info[0] == "service":
      self.send_html('<p>Path info : <code>{}</p><p>Chaîne de requête : <code>{}</code></p>' \
          .format('/'.join(self.path_info),self.query_string));

    else:
      self.send_static()


  # méthode pour traiter les requêtes HEAD
  def do_HEAD(self):
      self.send_static()


  # méthode pour traiter les requêtes POST - non utilisée dans l'exemple
  def do_POST(self):
    self.init_params()

    # requête générique
    if self.path_info[0] == "service":
      self.send_html(('<p>Path info : <code>{}</code></p><p>Chaîne de requête : <code>{}</code></p>' \
          + '<p>Corps :</p><pre>{}</pre>').format('/'.join(self.path_info),self.query_string,self.body));

    else:
      self.send_error(405)


  # on envoie le document statique demandé
  def send_static(self):

    # on modifie le chemin d'accès en insérant le répertoire préfixe
    self.path = self.static_dir + self.path

    # on appelle la méthode parent (do_GET ou do_HEAD)
    # à partir du verbe HTTP (GET ou HEAD)
    if (self.command=='HEAD'):
        http.server.SimpleHTTPRequestHandler.do_HEAD(self)
    else:
        http.server.SimpleHTTPRequestHandler.do_GET(self)


  # on envoie un document html dynamique
  def send_html(self,content):
     headers = [('Content-Type','text/html;charset=utf-8')]
     html = '<!DOCTYPE html><title>{}</title><meta charset="utf-8">{}' \
         .format(self.path_info[0],content)
     self.send(html,headers)

  # on envoie un contenu encodé en json
  def send_json(self,data,headers=[]):
    body = bytes(json.dumps(data),'utf-8') # encodage en json et UTF-8
    self.send_response(200)
    self.send_header('Content-Type','application/json')
    self.send_header('Content-Length',int(len(body)))
    [self.send_header(*t) for t in headers]
    self.end_headers()
    self.wfile.write(body) 

  # on envoie la réponse
  def send(self,body,headers=[]):
     encoded = bytes(body, 'UTF-8')

     self.send_response(200)

     [self.send_header(*t) for t in headers]
     self.send_header('Content-Length',int(len(encoded)))
     self.end_headers()

     self.wfile.write(encoded)


  # on analyse la requête pour initialiser nos paramètres
  def init_params(self):
    # analyse de l'adresse
    info = urlparse(self.path)
    self.path_info = [unquote(v) for v in info.path.split('/')[1:]]
    self.query_string = info.query
    self.params = parse_qs(info.query)

    # récupération du corps
    length = self.headers.get('Content-Length')
    ctype = self.headers.get('Content-Type')
    if length:
      self.body = str(self.rfile.read(int(length)),'utf-8')
      if ctype == 'application/x-www-form-urlencoded' : 
        self.params = parse_qs(self.body)
    else:
      self.body = ''
   
    # traces
    print('info_path =',self.path_info)
    print('body =',length,ctype,self.body)
    print('params =', self.params)
    
  def data_map(self):
    # création d'un curseur (conn est globale)
    c = conn.cursor()
    # récupération de la liste des pays dans la base
    c.execute("SELECT name, lat, long FROM countries")
    r = c.fetchall()
    data=[]
    for pays in r:
        lat=float((pays[1]))
        lon=float(pays[2])
        data.append({'name':pays[0],'lat':lat,'lon':lon})
    return data
    
  def get_description(self,country):
    # création d'un curseur (conn est globale)
    c = conn.cursor()
    # récupération de la liste des pays dans la base
    c.execute("SELECT * FROM countries WHERE name=?",(country,))
    r=c.fetchone()
    data={'name':r['name'],'capital':r['capital'],'lat':r['lat'],'lon':r['long'],'superficie':r['superficie'],'plus_grande_ville':r['plus_grande_ville'],'idh':r['IDH'],'wiki':'https://en.wikipedia.org/wiki/'+(r['name'].replace(' ','_')),'drapeau':r['drapeau']}
    if r['plus_grande_ville']=='capital':
        data['plus_grande_ville']=r['capital']
    return data
    
#
# Ouverture d'une connexion avec la base de données
#
conn = sqlite3.connect('pays.sqlite')

# Pour accéder au résultat des requêtes sous forme d'un dictionnaire
conn.row_factory = sqlite3.Row

# instanciation et lancement du serveur
httpd = socketserver.TCPServer(("", 8085), RequestHandler)
httpd.serve_forever()
