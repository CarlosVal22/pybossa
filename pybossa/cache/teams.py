# This file is part of PyBOSSA.
#
# PyBOSSA is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyBOSSA is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with PyBOSSA.  If not, see <http://www.gnu.org/licenses/>.
from sqlalchemy.sql import func, text
from pybossa.core import db
from pybossa.cache import cache, memoize, delete_memoized, ONE_DAY, ONE_HOUR
from flask.ext.login import current_user
from pybossa.model import User, Team, User2Team
from sqlalchemy import or_, func, and_
from operator import itemgetter

STATS_TIMEOUT=50

#@cache(timeout=ONE_HOUR, key_prefix="site_total_teams")

@memoize(timeout=ONE_HOUR)
def get_teams_count():
    count = Team.query.count()
    return count

@memoize(timeout=ONE_HOUR)
def get_teams_page(page, per_page=24):
    offset = (page - 1) * per_page
    sql = text('''SELECT team.id, team.name, team.description, team.owner_id,
               team.created, team.public, "user".fullname as owner_name  
               from team inner join "user" on team.owner_id="user".id 
               ORDER BY team.created DESC LIMIT :limit OFFSET :offset''')

    results = db.engine.execute(sql, limit=per_page, offset=offset)
    teams = []
    for row in results:
        team = dict(id=row.id, name=row.name, description=row.description,
                    owner_id=row.owner_id, owner_name=row.owner_name,
                    created=row.created, public=row.public)
        teams.append(team)
    return teams

@cache(key_prefix="teams_get_public_count")
def get_public_count():
    ''' Return number of Public Teams '''
    sql = text('''select count(*) from team where public;''')
    results = db.engine.execute(sql)
    for row in results:
        count = row[0]
    return count

#@cache.cached(key_prefix="teams_get_public_data")
def get_public_data(page=1, per_page=5):
    ''' Return a list of public teams with a pagination '''
    count = get_public_count()
    sql = text('''
               SELECT team.id,team.name,team.description,team.created,
               team.owner_id,"user".name as owner, team.public
               FROM team
               INNER JOIN "user" ON team.owner_id="user".id
               WHERE public
               order by team.name
               OFFSET(:offset) LIMIT(:limit);
               ''')

    offset = (page - 1) * per_page
    results = db.engine.execute(sql, limit=per_page, offset=offset)
    teams = []
    for row in results:
        team = dict(
            id=row.id,
            name=row.name,
            created=row.created,
            description=row.description,
            owner_id=row.owner_id,
            owner=row.owner,
			public=row.public
            )

        team['rank'], team['score'] = get_rank(row.id)
        team['members'] = get_number_members(row.id)
        team['total'] = get_teams_count()
        teams.append(team)

    return teams, count

@memoize()
def get_team_summary(name):
    ''' Get TEAM data '''
    sql = text('''
            SELECT team.id,team.name,team.description,team.created,
            team.owner_id,"user".fullname as owner, team.public
            FROM team
            INNER JOIN "user" ON team.owner_id="user".id
            WHERE team.name=:name
            ''')

    results = db.engine.execute(sql, name=name)
    team = dict()
    for row in results:
        team = dict(
            id=row.id,
            name=row.name,
            description=row.description,
            owner=row.owner,
            public=row.public,
            created=row.created
            )

        team['rank'], team['score'] = get_rank(row.id)
        team['members'] = get_number_members(row.id)
        team['total'] = get_teams_count()
        return team
    else:
        return None

@memoize()
def get_number_members(team_id):
    ''' Return number of Public Teams '''
    sql = text('''select count(*) from User2Team where team_id=:team_id;''')
    results = db.engine.execute(sql, team_id=team_id)
    for row in results:
        count = row[0]
    return count

@memoize()
def get_rank(team_id):
    ''' Score and Rank '''
    sql = text('''
               WITH  global_rank as(
               WITH scores AS(
               SELECT team_id, count(*) AS score FROM user2team
               INNER JOIN task_run ON user2team.user_id = task_run.user_id
               GROUP BY user2team.team_id )
               SELECT team_id,score,rank() OVER (ORDER BY score DESC)
               FROM  scores)
               SELECT  * from global_rank where team_id=:team_id;
               ''')

    results = db.engine.execute(sql, team_id=team_id)
    rank = 0
    score = 0
    if results:
        for result in results:
            rank  = result.rank
            score = result.score

	return rank, score

@memoize()
def get_team(name):
    ''' Get Team by name and owner '''
    if current_user.is_anonymous():
        return Team.query.filter_by(name=name, public=True).first_or_404()
    elif current_user.admin == 1:
       return Team.query.filter_by(name=name).first_or_404()
    else:
        return Team.query.filter(Team.name==name)\
                    .outerjoin(User2Team)\
                    .filter(or_ (Team.public ==True,\
                    User2Team.user_id == current_user.id))\
                    .first_or_404()

@memoize()
def user_belong_team(team_id):
    ''' Is a user belong to a team'''
    if  current_user.is_anonymous():
       return 0
    else:
        belong = User2Team.query.filter(User2Team.team_id==team_id)\
                                .filter(User2Team.user_id==current_user.id)\
                                .first()
        return (1,0)[belong is None]

@memoize()
def get_signed_teams(page=1, per_page=5):
    '''Return a list of public teams with a pagination'''
    sql = text('''
              SELECT count(*)
              FROM User2Team
              WHERE User2Team.user_id=:user_id;
              ''')

    results = db.engine.execute(sql, user_id=current_user.id)
    for row in results:
        count = row[0]

    sql = text('''
              SELECT team.id,team.name,team.description,team.created,
              team.owner_id,"user".name as owner, team.public
              FROM team
              JOIN user2team ON team.id=user2team.team_id
              JOIN "user" ON team.owner_id="user".id
              WHERE user2team.user_id=:user_id
              OFFSET(:offset) LIMIT(:limit);
              ''')

    offset = (page - 1) * per_page
    results = db.engine.execute(
            sql, limit=per_page, offset=offset, user_id=current_user.id)

    teams = []
    for row in results:
        team = dict(
                id=row.id,
                name=row.name,
                created=row.created,
                description=row.description,
                owner_id=row.owner_id,
                owner=row.owner,
                public=row.public
                )

        team['rank'], team['score'] = get_rank(row.id)
        team['members'] =get_number_members(row.id)
        teams.append(team)

    return teams, count

def get_private_teams(page=1, per_page=5):
    '''Return a list of public teams with a pagination'''
    sql = text('''
              SELECT count(*)
              FROM team
              WHERE not public;
              ''')
    results = db.engine.execute(sql)
    for row in results:
        count = row[0]
    sql = text('''
              SELECT team.id,team.name,team.description,team.created,
              team.owner_id,"user".name as owner, team.public
              FROM team
              INNER JOIN "user" ON team.owner_id="user".id
              WHERE not team.public
              order by team.name 
              OFFSET(:offset) LIMIT(:limit);
              ''')

    offset = (page - 1) * per_page
    results = db.engine.execute(sql, limit=per_page, offset=offset)
    teams = []
    for row in results:
        team = dict(
                id=row.id,
                name=row.name,
                created=row.created,
                description=row.description,
                owner_id=row.owner_id,
                owner=row.owner,
                public=row.public
                )

        team['rank'], team['score'] = get_rank(row.id)
        team['members'] =get_number_members(row.id)
        teams.append(team)

    return teams, count

@memoize()
def get_users_teams_detail(team_id):
    # Search users in the team
    sql = text('''
              SELECT user2team.user_id, user2team.created,"user".name, "user".fullname
              FROM user2team
              INNER JOIN "user" on user2team.user_id="user".id
              WHERE user2team.team_id=:team_id;
              ''')

    results = db.engine.execute(sql, team_id=team_id)
    users = []
    
    for row in results:
        user = dict()
        user = dict(id=row.user_id,
                    name=row.name,
                    fullname=row.fullname,
                    created=row.created,
                    rank=0, score=0
                    )

        # Get Rank and Score
        sql = text('''
                    WITH global_rank AS (
                        WITH scores AS (
                            SELECT user_id, COUNT(*) AS score FROM task_run
                            WHERE user_id IS NOT NULL GROUP BY user_id)
                        SELECT user_id, score, rank() OVER (ORDER BY score desc)
                        FROM scores)
                    SELECT * from global_rank WHERE user_id=:user_id;
                    ''')

        results_rank = db.engine.execute(sql, user_id=row.user_id)
        for row_rank in results_rank:
            user['rank'] = row_rank.rank
            user['score'] = row_rank.score

        users.append(user)

    # Sort list by score
    if users:
        users = sorted(users, key=itemgetter('score'), reverse=True ) 

    return users

def reset():
    ''' Clean thie cache '''
    #cache.delete('teams_get_public_count')
    #cache.delete('teams_get_count')
    #cache.delete('teams_get_public_data')
    #cache.delete_memoized(get_number_members)
    #cache.delete_memoized(get_rank)
    #cache.delete_memoized(get_team)
    #cache.delete_memoized(user_belong_team)
    #cache.delete_memoized(get_signed_teams)
    #cache.delete_memoized(get_private_teams)
    #cache.delete_memoized(get_team_summary)
    #cache.delete_memoized( get_users_teams_detail);

def delete_team(team_id):
    ''' Reset team values in cache '''
    #cache.delete_memoized(get_team, team_id)

def clean(team_id):
    ''' Clean all items in cache '''
    reset()

def delete_team_summary():
    """Delete from cache the team summary."""
    delete_memoized(get_teams_count)
    delete_memoized(get_teams_page)
