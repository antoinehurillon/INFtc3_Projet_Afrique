# Projet Afrique/serveur.pu
# Partie serveur
# Par Antoine HURILLON


#%% import des bibilothèques nécessaires
import http.server
import socketserver
import sqlite3
import json

from urllib.parse import urlparse, parse_qs, unquote



#%% Définition du nouveau handler grâce à une classe

class RequestHandler(http.server.SimpleHTTPRequestHandler):

  # sous-répertoire racine des documents statiques
  static_dir = '/client'

  # version du serveur
  server_version = 'countries/0.1'

  
  # On surcharge la méthode qui traite les requêtes GET
  
  def do_GET(self):
    # on récupère les paramètres
    self.init_params()

    # le chemin d'accès commence par /countries
    if self.path.startswith('/countries'):
      self.send_countries()

    # le chemin d'accès commence par /country et se poursuit par un nom de pays
    elif self.path_info[0] == 'country' and len(self.path_info) > 1:
      self.send_country(self.path_info[1])
      
    # le chemin d'accès commence par /service/countries/...
    elif self.path_info[0] == 'service' and self.path_info[1] == 'countries' and len(self.path_info) > 1:
      continent = self.path_info[2] if len(self.path_info) > 2 else None
      self.send_json_countries(continent)           #pour l'initialisation

    # le chemin d'accès commence par /service/country/...
    elif self.path_info[0] == 'service' and self.path_info[1] == 'country' and len(self.path_info) > 2:
      self.send_json_country(self.path_info[2])     #pour les infos après avoir cliqué sur une icone

    #mais pas toujours
    else:
      self.send_static()

  
  # On surcharge la méthode qui traite les requêtes HEAD
  
  def do_HEAD(self):
    self.send_static()

  
  # On envoie le document statique demandé
  
  def send_static(self):

    # on modifie le chemin d'accès en insérant un répertoire préfixe
    self.path = self.static_dir + self.path

    # on appelle la méthode parent (do_GET ou do_HEAD)
    # à partir du verbe HTTP (GET ou HEAD)
    if (self.command=='HEAD'):
        http.server.SimpleHTTPRequestHandler.do_HEAD(self)
    else:
        http.server.SimpleHTTPRequestHandler.do_GET(self)
        

       
  # on analyse la requête pour initialiser nos paramètres
  
  def init_params(self):
    # analyse de l'adresse
    info = urlparse(self.path)
    self.path_info = [unquote(v) for v in info.path.split('/')[1:]]  # info.path.split('/')[1:]
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
    print('path_info =',self.path_info)
    print('body =',length,ctype,self.body)
    print('params =', self.params)


  
  # On renvoie la liste des pays avec leurs coordonnées
  
  def send_json_countries(self,continent):

    # on récupère la liste de pays depuis la base de données
    r = self.db_get_countries(continent)

    # on renvoie une liste de dictionnaires au format JSON
    data = [ {k:a[k] for k in a.keys()} for a in r]
    json_data = json.dumps(data, indent=4)
    headers = [('Content-Type','application/json')]
    self.send(json_data,headers)

  #
  # On renvoie la liste des pays
  #
  def send_countries(self):

    # récupération de la liste des pays dans la base
    r = self.db_get_countries()

    # construction de la réponse
    txt = 'List of all {} countries :\n'.format(len(r))
    n = 0
    for a in r:
       n += 1
       txt = txt + '[{}] - {}\n'.format(n,a[0])
    
    # envoi de la réponse
    headers = [('Content-Type','text/plain;charset=utf-8')]
    self.send(txt,headers)

  
  # On renvoie les informations d'un pays
  
  def send_country(self,country):

    # on récupère le pays depuis la base de données
    r = self.db_get_country(country)

    # on n'a pas trouvé le pays demandé
    if r == None:
      self.send_error(404,'Country not found')

    # on génère un document au format html
    else:
      body = '<!DOCTYPE html>\n<meta charset="utf-8">\n'
      body += '<title>{}</title>'.format(country)
      body += '<link rel="stylesheet" href="/TD2-s8.css">'
      body += '<main>'
      body += '<h1>{}</h1>'.format(r['wp'])
      body += '<ul>'
      body += '<li>{}: {}</li>'.format('Continent',r['continent'].capitalize())
      body += '<li>{}: {}</li>'.format('Capital',r['Capital'])
      body += '<li>{}: {:.3f}</li>'.format('Latitude',r['Latitude'])
      body += '<li>{}: {:.3f}</li>'.format('Longitude',r['Longitude'])
      body += '<li>{}: {}</li>'.format('Currency',r['Currency'])
      body += '<li>{}: {}</li>'.format('Area',r['Area'])
      body += '<li>{}: {}</li>'.format('Government_type',r['Government_type'])
      body += '<li>{}: {}</li>'.format('GDP_nominal',r['GDP_nominal'])
      body += '<li>{}: {}</li>'.format('Name',r['Name'])
      body += '<li>{}: {}</li>'.format('Flag',r['Flag'])
      body += '</ul>'
      body += '</main>'

      # on envoie la réponse
      headers = [('Content-Type','text/html;charset=utf-8')]
      self.send(body,headers)

  
  # On renvoie les informations d'un pays au format json
  
  def send_json_country(self,country):

    # on récupère le pays depuis la base de données
    r = self.db_get_country(country)

    # on n'a pas trouvé le pays demandé
    if r == None:
      self.send_error(404,'Country not found')

    # on renvoie un dictionnaire au format JSON
    else:
      data = {k:r[k] for k in r.keys()}
      json_data = json.dumps(data, indent=4)
      headers = [('Content-Type','application/json')]
      self.send(json_data,headers)


  
  # Récupération de la liste des pays depuis la base
  
  def db_get_countries(self,continent=None):
    c = conn.cursor()
    sql = 'SELECT wp, Name, capital, latitude, longitude, currency, area, government_type, GDP_nominal from countries'

    # les pays d'un continent
    if continent:
      sql += ' WHERE continent LIKE ?'
      c.execute(sql,('%{}%'.format(continent),))

    # tous les pays de la base
    else:
      c.execute(sql)

    return c.fetchall()


  #
  # Récupération d'un pays dans la base
  #
  def db_get_country(self,country):
    # préparation de la requête SQL
    c = conn.cursor()
    sql = 'SELECT * from countries WHERE wp=?'

    # récupération de l'information (ou pas)
    c.execute(sql,(country,))
    return c.fetchone()
  


  
  # On envoie les entêtes et le corps fourni
  
  def send(self,body,headers=[]):

    # on encode la chaine de caractères à envoyer
    encoded = bytes(body, 'UTF-8')

    self.send_raw(encoded,headers)

  def send_raw(self,data,headers=[]):
    # on envoie la ligne de statut
    self.send_response(200)

    # on envoie les lignes d'entête et la ligne vide
    [self.send_header(*t) for t in headers]
    self.send_header('Content-Length',int(len(data)))
    self.end_headers()

    # on envoie le corps de la réponse
    self.wfile.write(data)


 

#%% Ouverture d'une connexion avec la base de données

conn = sqlite3.connect('pays.sqlite')

# Pour accéder au résultat des requêtes sous forme d'un dictionnaire
conn.row_factory = sqlite3.Row

#
# Instanciation et lancement du serveur
#
httpd = socketserver.TCPServer(("", 8080), RequestHandler)
httpd.serve_forever()

