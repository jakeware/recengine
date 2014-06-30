#!/usr/bin/env python

import csv
import sys
import pprint
import argparse
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
verbose = True
debug = False
quiet = False
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
        print 'Matches:'
        print self.matches

# read input file with user provided data
def userParseData(filename):
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
    title = mov.titles['user']
    title = unicode(title, in_encoding, 'replace')
    try:
        # Do the search, and get the results (a list of Movie objects).
        results = i.search_movie(title)
    except imdb.IMDbError, e:
        print "You might not be connected to the internet.  Complete error report:"
        print e
        sys.exit(3)

    # print search results
    if debug:
        # Print the results.
        print '    %s result%s for "%s":' % (len(results),('', 's')[len(results) != 1],title.encode(out_encoding, 'replace'))
        print 'movieID\t: imdbID : title'

        # Print the long imdb title for every movie.
        for res in results_imdb:
            outp = u'%s\t: %s : %s' % (res.movieID, i.get_imdbID(res), res['long imdb title'])
            print outp.encode(out_encoding, 'replace')

    return results

# get data by ID
def imdbGetData(mov, res_imdb):
    try:
        mov_imdb = i.get_movie(res_imdb.movieID)
    except imdb.IMDbError, e:
        print "Probably you're not connected to Internet.  Complete error report:"
        print e
        sys.exit(3)

    # ID
    mov.idnum['imdb'] = mov_imdb['id']
    if debug:
        print 'ID:'
        print mov.idnum

    # TITLE
    mov.titles['imdb'] = mov_imdb['title']
    if debug:
        print 'Title:'
        print mov.titles

    # YEAR
    mov.year['imdb'] = mov_imdb['year']
    if debug:
        print 'Year:'
        print mov.year

    # DIRECTORS
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
    imdb_genres = mov_imdb['genres']
    for v in imdb_genres:
        if debug:
            print v
        mov.genres['imdb'].append(v)
    if debug:
        print 'Genres:'
        print mov.genres

    # RUNTIME
    mov.runtime['imdb'] = mov_imdb['runtime']
    if debug:
        print 'Runtime:'
        print mov.runtime

    # RATINGS
    mov.ratings['imdb'] = mov_imdb['rating']
    if debug:
        print 'Ratings:'
        print mov.ratings

def rtSearch(mov):
    results_rt = rt.search(mov.titles['user'], page_limit=2)

    return results_rt

def rtParseData(mov,res_rt):
    mov.idnum['rt'] = res_rt['id']
    mov.ratings['rt_critics'] = res_rt['ratings']['critics_score']
    mov.ratings['rt_audience'] = res_rt['ratings']['audience_score']

def mcSearch(mov):
    response = unirest.post("https://byroredux-metacritic.p.mashape.com/find/movie",
        headers={"X-Mashape-Key": "kGxeWQbWwmmsh4F8qlBKNauJrroDp15JQmJjsnBvabUYb5j9aY"},
        params={"retry": 4, "title": mov.titles['imdb']})

    res_mc = response.body['result']

    return res_mc

def mcGetData(mov,res_mc):
    mov.ratings['mc_score'] = res_mc['score']
    mov.ratings['mc_userscore'] = res_mc['userscore']

def main():
    print 'loading data...'
    movies = userParseData(infile)
    print 'done loading data'
    print 'gathering data from sources...'

    # loop through all movies in user database
    for mov in movies:
        # IMDB
        if debug:
            print 'searching IMDB...'

        # search by movie title
        results_imdb = imdbSearch(mov)

        # look for exact match in search results
        for res_imdb in results_imdb[:search_depth]:
            if res_imdb['title'] == mov.titles['user']:
                mov.matches['imdb'] = True
                if debug:
                    print 'title:{} matched to {}'.format(mov.titles['user'], res_imdb['title'])
                    print 'fetching imdb movie data...'
                imdbGetData(mov,res_imdb)
            else:
                mov.matches['rt'] = False
                if debug:
                    print '{} not in titles for {}'.format(mov.titles['user'],res_imdb['title'])

            # break if we found the movie
            if mov.matches['imdb'] == True:
                break

        # RT
        if debug:
            print 'searching rotten tomatoes...'

        # search by movie title
        results_rt = rtSearch(mov)

        # look for exact match in search results
        for res_rt in results_rt[:search_depth]:
            if res_rt['title'] == mov.titles['user']:
                mov.matches['rt'] = True
                if debug:
                    print 'title:{} matched to {}'.format(mov.titles['user'], res_rt['title'])
                    print 'fetching imdb movie data...'
                rtGetData(mov,res_rt)
            else:
                mov.matches['rt'] = False
                if debug:
                    print '{} not in titles for {}'.format(mov.titles['user'],res_rt['title'])

            # break if we found the movie
            if mov.matches['rt'] == True:
                break


        # MC
        if debug:
            print 'searching metacritic...'

        # search by movie title
        res_mc = mcSearch(mov)

        # look for exact match in search results
        if res_mc['name'] == mov.titles['user']:
            mov.matches['mc'] = True
            if debug:
                print 'title:{} matched to {}'.format(mov.titles['user'], res_mc['name'])
                print 'fetching imdb movie data...'
            mcGetData(mov,res_mc)
        else:
            mov.matches['mc'] = False

        # print final results
        if verbose:
            print 'summary:'
            mov.summary()

        # break because we only want to do the first movie in test phase...
        break

    if __name__ == "__main__":
        main()
