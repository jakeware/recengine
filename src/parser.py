#!/usr/bin/env python

import csv
import sys
import pprint
import argparse
import time
from collections import defaultdict
try:
    from rottentomatoes import RT
except ImportError:
    print 'Import Error: Install the rottentoamtoes package'
    sys.exit(1)
try:
    import imdb
except ImportError:
    print 'Import Error: Install the IMDbPY package'
    sys.exit(1)
try:
    import unirest
except ImportError:
    print 'Import Error: Install the unirest package'
    sys.exit(1)

# general setup
infile = '../data/data_2014-06-18.csv'
outfile = '../data/data_output.txt'
verbose = False
debug = False
quiet = False
stop_count = 50
raters = ['Jon','Jeff','Jake','Shu','iMDB','MC','RT','SVH','AKF','DC']
cast_depth = 2
search_depth = 5

# pretty print setup
pp = pprint.PrettyPrinter(indent=2)

# imdbpy setup
i = imdb.IMDb()
in_encoding = sys.stdin.encoding or sys.getdefaultencoding()
out_encoding = sys.stdout.encoding or sys.getdefaultencoding()

# rottentomatoes setup
rt = RT('s3jzubak8mqzjvkxm83xv57r')  # jake's rottentomatoes api key

class Movie:
    def __init__(self):
        self.titles = dict()
        self.year = dict()
        self.directors = dict()
        self.cast = dict()
        self.genres = defaultdict(list)
        self.runtime = dict()
        self.idnum = dict()
        self.ratings = dict()
        self.mpaa = dict()
        self.matches = dict()

    def addDirector(self, tup):
        if not self.directors.has_key(tup[0]):
            self.directors[tup[0]] = {}
        self.directors[tup[0]][tup[1]] = [tup[2]]

    def addCast(self, tup):
        if not self.cast.has_key(tup[0]):
            self.cast[tup[0]] = {}
        self.cast[tup[0]][tup[1]] = [tup[2]]

    def summary(self):
        print 'Title: '
        print self.titles
        print 'Year: '
        print self.year
        print 'Directors: '
        print self.directors
        print 'Cast: '
        print self.cast
        print 'Genres: '
        print self.genres
        print 'Runtime: '
        print self.runtime
        print 'ID: '
        print self.idnum
        print 'Ratings: '
        print self.ratings
        print 'MPAA: '
        print self.mpaa
        print 'Matches:'
        print self.matches

# read input file with user provided data
def userParseData(filename):
    print 'loading data...'
    with open(filename, 'rb') as csvfile:
        reader = csv.reader(csvfile, delimiter=',', quotechar='|')

        movies = []
        rownum = 0
        for row in reader:
            if rownum == 0:
                header = row
            else:
                temp_movie = Movie()
                colnum = 0
                for col in row:
                    if col:
                        if "Title" in header[colnum]:
                            temp_movie.titles['user'] = col
                        elif "Year" in header[colnum]:
                            temp_movie.year['user'] = col
                        elif "Genre" in header[colnum]:
                            temp_movie.genres['user'].append(col)
                        elif "Length" in header[colnum]:
                            temp_movie.runtime['user'] = col
                        elif "ID" in header[colnum]:
                            temp_movie.idnum['user'] = col
                        elif header[colnum] in raters:
                            temp_movie.ratings[header[colnum]] = float(col)
                    colnum += 1
                movies.append(temp_movie)
            rownum += 1

    return movies

def imdbSearch(mov):
    if debug:
        print 'searching IMDB...'

    title = mov.titles['user']
    title = unicode(title, in_encoding, 'replace')
    try:
        # Do the search, and get the results (a list of Movie objects).
        results_imdb = i.search_movie(title)
    except imdb.IMDbError, e:
        print "imdbSearch failed"
        print e
        return False

    # print search results
    if debug:
        # Print the results.
        print '    %s result%s for "%s":' % (len(results_imdb),('', 's')[len(results_imdb) != 1],title.encode(out_encoding, 'replace'))
        print 'movieID\t: imdbID : title'

        # Print the long imdb title for every movie.
        for res in results_imdb:
            outp = u'%s\t: %s : %s' % (res.movieID, i.get_imdbID(res), res['long imdb title'])
            print outp.encode(out_encoding, 'replace')

    return results_imdb

def imdbMatch(mov,results_imdb,search_depth):
    if not results_imdb:
        mov.matches['imdb'] = False
        return

    for res_imdb in results_imdb[:search_depth]:
        if res_imdb['title'] == mov.titles['user']:
            mov.matches['imdb'] = True
            if debug:
                print 'title:{} matched to {}'.format(mov.titles['user'], res_imdb['title'])
                print 'fetching imdb movie data...'
            imdbGetData(mov,res_imdb)
            return
        else:
            mov.matches['imdb'] = False

    if debug:
        print '{} not in titles for {}'.format(mov.titles['user'],res_imdb['title'])
    return

# get data by ID
def imdbGetData(mov, res_imdb):
    try:
        mov_imdb = i.get_movie(res_imdb.movieID)
    except imdb.IMDbError, e:
        print "imdbGetData failed"
        print e
        return False

    #print mov_imdb.keys()

    # ID
    mov.idnum['imdb'] = mov_imdb.movieID
    if debug:
        print 'ID:'
        print mov.idnum

    # TITLE
    if 'title' in mov_imdb:
        mov.titles['imdb'] = mov_imdb['title']
    if debug:
        print 'Title:'
        print mov.titles

    # YEAR
    if 'year' in mov_imdb:
        mov.year['imdb'] = mov_imdb['year']
    if debug:
        print 'Year:'
        print mov.year

    # DIRECTORS
    if 'director' in mov_imdb:
        imdb_director = mov_imdb['director']
        for v in imdb_director:
            if debug:
                print v['name']
                print v.getID()
            mov.addDirector(('imdb',v['name'],v.getID()))
    if debug:
        print 'Directors:'
        print mov.directors

    # CAST
    if 'cast' in mov_imdb:
        imdb_cast = mov_imdb['cast']
        for v in imdb_cast[:cast_depth]:
            if debug:
                print v['name']
                print v.getID()
            mov.addCast(('imdb',v['name'],v.getID()))
    if debug:
        print 'Cast:'
        print mov.cast

    # GENRES
    if 'genres' in mov_imdb:
        imdb_genres = mov_imdb['genres']
        for v in imdb_genres:
            if debug:
                print v
            mov.genres['imdb'].append(v)
    if debug:
        print 'Genres:'
        print mov.genres

    # RUNTIME
    if 'runtime' in mov_imdb:
        mov.runtime['imdb'] = mov_imdb['runtime']
    if debug:
        print 'Runtime:'
        print mov.runtime

    # RATINGS
    if 'rating' in mov_imdb:
        mov.ratings['imdb'] = mov_imdb['rating']
    if debug:
        print 'Ratings:'
        print mov.ratings

def rtSearch(mov):
    if debug:
        print 'searching rotten tomatoes...'

    try:
        results_rt = rt.search(mov.titles['user'], page_limit=2)
    except:
        print 'WARNING: rtSearch failed for: ' + mov.titles['user']
        pp.pprint(results_rt)
        return False

    return results_rt

def rtMatch(mov,results_rt,search_depth):
    if not results_rt:
        mov.matches['rt'] = False
        return
    else:
        for res_rt in results_rt[:search_depth]:
            if res_rt['title'] == mov.titles['user']:
                mov.matches['rt'] = True
                if debug:
                    print 'title:{} matched to {}'.format(mov.titles['user'], res_rt['title'])
                    print 'fetching rt movie data...'
                rtGetData(mov,res_rt)
                return
            else:
                mov.matches['rt'] = False

        if debug:
            print '{} not in titles for {}'.format(mov.titles['user'],res_rt['title'])
        return

def rtGetData(mov,res_rt):
    # get data by id
    try:
        mov_rt = rt.info(res_rt['id'])
    except:
        print 'WARNING: rtGetData failed for: ' + mov.titles['user']
        return False

    #pp.pprint(res_rt)

    # ID
    if 'id' in mov_rt:
        mov.idnum['rt'] = mov_rt['id']
    if debug:
        print 'ID:'
        print mov.idnum

    # TITLE
    if 'title' in mov_rt:
        mov.titles['rt'] = mov_rt['title']
    if debug:
        print 'Title:'
        print mov.titles

    # YEAR
    if 'year' in mov_rt:
        mov.year['rt'] = mov_rt['year']
    if debug:
        print 'Year:'
        print mov.year

    # DIRECTORS
    if 'abridged_directors' in mov_rt:
        rt_director = mov_rt['abridged_directors']
        for v in rt_director:
            if debug:
                print v['name']
            mov.addDirector(('rt',v['name'],None))
    if debug:
        print 'Directors:'
        print mov.directors

    # CAST
    if 'abridged_cast' in mov_rt:
        rt_cast = mov_rt['abridged_cast']
        for v in rt_cast[:cast_depth]:
            if debug:
                print v['name']
                print v['id']
            mov.addCast(('rt',v['name'],v['id']))
    if debug:
        print 'Cast:'
        print mov.cast

    # GENRES
    if 'genres' in mov_rt:
        rt_genres = mov_rt['genres']
        for v in rt_genres:
            if debug:
                print v
            mov.genres['rt'].append(v)
    if debug:
        print 'Genres:'
        print mov.genres

    # RUNTIME
    if 'runtime' in mov_rt:
        mov.runtime['rt'] = mov_rt['runtime']
    if debug:
        print 'Runtime:'
        print mov.runtime

    # RATINGS
    if 'ratings' in mov_rt:
        if 'critics_score' in mov_rt['ratings']:
            mov.ratings['rt_critics'] = mov_rt['ratings']['critics_score']
        if 'audience_score' in mov_rt['ratings']:
            mov.ratings['rt_audience'] = mov_rt['ratings']['audience_score']
    if debug:
        print 'Ratings:'
        print mov.ratings

def mcSearch(mov):
    if debug:
        print 'searching metacritic...'

    try:
        response = unirest.post("https://byroredux-metacritic.p.mashape.com/find/movie",
                    headers={"X-Mashape-Key": "kGxeWQbWwmmsh4F8qlBKNauJrroDp15JQmJjsnBvabUYb5j9aY"},
                    params={"retry": 4, "title": mov.titles['user']})
    except:
        print 'mcSearch failed'
        res_mc = False

    if 'result' in response.body.keys():
        res_mc = response.body['result']
    else:
        res_mc = False

    return res_mc

# search depth not used because only one result is returned from search
def mcMatch(mov,res_mc,search_depth):
    if not res_mc:
        mov.matches['mc'] = False
        return
    else:
        if res_mc['name'] == mov.titles['user']:
            mov.matches['mc'] = True
            if debug:
                print 'title:{} matched to {}'.format(mov.titles['user'], res_mc['name'])
                print 'fetching mc movie data...'
            mcGetData(mov,res_mc)
        else:
            mov.matches['mc'] = False

    return

def mcGetData(mov,res_mc):
    #pp.pprint(res_mc)

    # ID
    # NA

    # TITLE
    if 'name' in 'res_mc':
        mov.titles['mc'] = res_mc['name']
    if debug:
        print 'Title:'
        print mov.titles

    # YEAR
    # NA

    # DIRECTORS
    # need to parse string

    # CAST
    # need to parse string

    # GENRES
    # need to parse string

    # RUNTIME
    # need to parse string

    # RATINGS
    if 'score' in res_mc:
        mov.ratings['mc_score'] = res_mc['score']
    if 'userscore' in res_mc:
        mov.ratings['mc_userscore'] = res_mc['userscore']
    if debug:
        print 'Ratings:'
        print mov.ratings

def printSummary(mov,quiet,verbose):
    # print short summary
    if not quiet:
        print mov.titles['user']
        print mov.matches

    # print final results
    if verbose:
        print 'summary:'
        mov.summary()
        print 'sleeping...'

    time.sleep(2)

def main():
    # parse user data
    movies = userParseData(infile)

    print 'gathering data from sources...'
    # loop through all movies in user database and get data from sources
    for i, m in enumerate(movies):
        # only want to do the n movies in test phase...
        if i > stop_count:
            sys.exit(0)

        # IMDB
        results_imdb = imdbSearch(m)  # search by movie title
        imdbMatch(m,results_imdb,search_depth)  # look for exact match in search results and get data

        # RT
        results_rt = rtSearch(m)  # search by movie title
        rtMatch(m,results_rt,search_depth)  # look for exact match in search results and get data

        # MC
        results_mc = mcSearch(m)  # search by movie title
        mcMatch(m,results_mc,search_depth)  # look for exact match in search results and get data

        # SUMMARY
        printSummary(m,quiet,verbose)

if __name__ == "__main__":
    main()
