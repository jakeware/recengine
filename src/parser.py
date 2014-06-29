#!/usr/bin/env python

import csv
import sys
import pprint
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
verbose = True
debug = False
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
        self.year = 0
        self.directors = dict()
        self.cast = dict()
        self.genres = dict()
        self.runtime = 0
        self.idnum = dict()
        self.ratings = dict()

# read movie data file
print 'loading data...'
with open('../data/data_2014-06-18.csv', 'rb') as csvfile:
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
                        temp_movie.year = int(col)
                    elif "Director" in header[colnum]:
                        temp_movie.directors['user'] = col
                    elif "Actor" in header[colnum]:
                        temp_movie.cast['user'] = col
                    elif "Genre" in header[colnum]:
                        temp_movie.genres[col] = 'user'
                    elif "Length" in header[colnum]:
                        temp_movie.runtime = int(col)
                    elif "ID" in header[colnum]:
                        temp_movie.idnum[col] = 'user'
                    elif header[colnum] in raters:
                        temp_movie.ratings[header[colnum]] = float(col)
                colnum += 1
            movies.append(temp_movie)
        rownum += 1

print 'done loading'

# lookup movie ids
print 'searching for title matches...'
for mov in movies:
    title = mov.titles['user']
    title = unicode(title, in_encoding, 'replace')
    try:
        # Do the search, and get the results (a list of Movie objects).
        results_imdb = i.search_movie(title)
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

    # look for exact match in search results
    for res_imdb in results_imdb[:]:
        # debug stuff
        #pp.pprint(res_imdb)
        #print res_imdb.summary()
        #print res_imdb.keys()

        # does title of search result match?
        if mov.titles['user'] == res_imdb['title']:
            if verbose:
                print 'title:{} matched to {}'.format(mov.titles['user'], res_imdb['title'])

            # ID
            if verbose:
                print 'ID:'
            if not mov.idnum:
                if verbose:
                    print 'no user data'
                mov.id = res_imdb.movieID
            elif mov.id == res_imdb.movieID:
                if verbose:
                    print 'matching user data'
            else:
                if verbose:
                    print 'id:{} does not match user data: {}'.format(mov.id[0],res_imdb.movieID)

            # get movie by id
            print 'fetching imdb movie data...'
            try:
                # Get a Movie object with the data about the movie identified by
                # the given movieID.
                mov_imdb = i.get_movie(res_imdb.movieID)
            except imdb.IMDbError, e:
                print "Probably you're not connected to Internet.  Complete error report:"
                print e
                sys.exit(3)

            mov.idnum[res_imdb.movieID] = 'imdb'

            if verbose:
                print mov.idnum

            # TITLE
            if verbose:
                print 'Title:'

            imdb_title = mov_imdb['title']
            mov.titles['imdb'] = imdb_title

            if verbose:
                print imdb_title

            # YEAR
            if verbose:
                print 'Year:'

            imdb_year = mov_imdb['year']
            if not mov.year:
                if verbose:
                    print 'no user data'
                mov.year = imdb_year
            elif mov.year == imdb_year:
                if verbose:
                    print 'matching user data'
            else:
                if verbose:
                    print 'year:{} does not match user data: {}'.format(mov.year,imdb_year)

            if verbose:
                print mov.year

            # DIRECTORS
            if verbose:
                print 'Directors:'

            imdb_director = mov_imdb['director']
            #print imdb_director

            # loop through imdb directors
            for v in imdb_director:
                if verbose:
                    print v['name']
                    print v.getID()

                mov.directors[v.getID()] = v['name']

            if verbose:
                print mov.directors

            # CAST
            if verbose:
                print 'Cast:'

            imdb_cast = mov_imdb['cast']
            #print imdb_cast

            # loop through imdb cast
            for v in imdb_cast[:cast_depth]:
                if verbose:
                    print v['name']
                    print v.getID()

                mov.cast[v.getID()] = v['name']

            if verbose:
                print mov.cast

            # GENRES
            if verbose:
                print 'Genres:'

            imdb_genres = mov_imdb['genres']
            #print imdb_genres

            for v in imdb_genres:
                print v
                mov.genres[v] = 'imdb'

            if verbose:
                print mov.genres

            # RUNTIME
            if verbose:
                print 'Runtime:'

            imdb_runtime = mov_imdb['runtime']
            #print imdb_runtime

            mov.runtime = int(imdb_runtime[0])

            if verbose:
                print mov.runtime

            # RATINGS
            if verbose:
                print 'Ratings:'

            # imdb
            imdb_rating = mov_imdb['rating']
            mov.ratings['imdb'] = imdb_rating

            # rotten tomatoes
            if verbose:
                print 'searching rotten tomatoes...'

            results_rt = rt.search(mov.titles['user'], page_limit=2)
            #pp.pprint(rt_mov)

            for res_rt in results_rt[:search_depth]:
                if res_rt['title'] == mov.titles['imdb']:
                    mov.idnum['rt'] = res_rt['id']
                    mov.ratings['rt_critics'] = res_rt['ratings']['critics_score']
                    mov.ratings['rt_audience'] = res_rt['ratings']['audience_score']

            # meta-critic
            if verbose:
                print 'searching metacritic...'

            response = unirest.post("https://byroredux-metacritic.p.mashape.com/find/movie",
                                    headers={"X-Mashape-Key": "kGxeWQbWwmmsh4F8qlBKNauJrroDp15JQmJjsnBvabUYb5j9aY"},
                                    params={"retry": 4, "title": mov.titles['imdb']}
                                )
            res_mc = response.body['result']

            # check title
            if res_mc['name'] == mov.titles['imdb']:
                mov.ratings['mc_score'] = res_mc['score']
                mov.ratings['mc_userscore'] = res_mc['userscore']

            if verbose:
                print mov.ratings

            # break since we found the movie we are looking for and got data
            break

        # incorrect search result
        else:
            print '{} not in titles for {}'.format(mov.titles['user'],res_imdb['title'])

    break
