from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import urlfetch
import os, urllib, datetime, calendar, simplejson,md5

def mostAct(email,acts): 
	acts = [x for x in acts if x['verb'] == 'recommended']
	lookup = dict([ (item['object_url'],(item['object'],item['object_desc'])) for item in acts ])
	urls = dict([ (item['object_url'],0) for item in acts ])
	for item in acts:
		urls[item['object_url']] +=1
	urls = sorted([ (v,k) for (k,v) in urls.iteritems() ])
	result = []
	for (count,url) in urls[-10:][::-1]:
		item = {"email": email , "url":url , "count": str(count),  "title" : lookup[url][0], "selection" : lookup[url][1]}
		#escaping for " for YQL
		clean = dict([(k,v.replace('"','\\"').encode('UTF-8')) for (k,v) in item.iteritems() if  v !=None ]) 
		if 'selection' not in clean:
			clean['selection'] = '' 
		result.append(clean)	
	return result[::-1]

def executeYQL(YQL): 
	params = urllib.urlencode({"q":YQL,"format":"json", "env" : "store://datatables.org/alltableswithkeys" ,"callback":""})
	url = "http://query.yahooapis.com/v1/public/yql"
	data = simplejson.loads(urlfetch.fetch( url + "?"+ params,).content)
	return data['query']['results']

class SyncPage(webapp.RequestHandler):
	def get(self):
		email = self.request.get("email");
		results = [] 
		error = "" 
		if email !=None and email.strip() != '': 
			email = email.strip()
			try: 
				user = executeYQL('select * from nyt.people.users where email-hash="%s"' % md5.md5(email).hexdigest()) ['user_id']
				acts = executeYQL("select * from nyt.people.newsfeed where user-id=%s " % user) ['activity']
				updates = mostAct(email,acts)
				for item in updates:
					response = executeYQL('insert into instapaper.unread (username,url,title,selection) VALUES ("%(email)s", "%(url)s","%(title)s","%(selection)s || Recommended by: %(count)s")' % item)
					if response['result'].strip() == '201':
						results.append(item)
					else:
						error = "Can't find InstaPaper Account for %s " % email
			except Exception, e:
				error = "Unable to locate TimesPeople for %s"	 % email
		self.response.out.write(template.render('template.html', {"results": results,"email":email, "error" : error, "nresults" : len(results)}))
		
def main():
    application = webapp.WSGIApplication([('/', SyncPage)], debug=True)
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
