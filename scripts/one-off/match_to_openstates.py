#!/usr/bin/env python

import csv
import os
import glob
from collections import defaultdict
import click
from utils import get_data_dir, load_yaml, role_is_active, get_all_abbreviations, dump_obj


def get_chamber_and_district(person):
    for role in person['roles']:
        if role_is_active(role):
            return role['type'], role['district']


class Matcher:
    def __init__(self, abbr):
        self.abbr = abbr
        self.people_by_name = defaultdict(list)
        self.people_by_id = {}
        self.load_from_csv(os.path.join(os.path.dirname(__file__), 'legacy_openstates_ids.csv'))

    def load_from_csv(self, csvname):
        with open(csvname) as f:
            data = csv.DictReader(f)
            for line in data:
                if line['active'] == 'True' and line['state'] == self.abbr:
                    self.load_person(line)

    def load_person(self, line):
        self.people_by_name['{first_name} {last_name}'.format(**line)].append(line['id'])
        if line['middle_name']:
            self.people_by_name['{first_name} {middle_name} {last_name}'.format(**line)].append(line['id'])
        if line['suffixes']:
            self.people_by_name['{first_name} {last_name} {suffixes}'.format(**line)].append(line['id'])
        if line['middle_name'] and line['suffixes']:
            self.people_by_name['{first_name} {middle_name} {last_name} {suffixes}'.format(**line)].append(line['id'])

        self.people_by_id[line['id']] = line

    def match(self, person):
        potentials = self.people_by_name[person['name']]
        chamber, district = get_chamber_and_district(person)
        exact = []
        if len(potentials) == 0:
            click.secho(f'no known match for {person["name"]}', fg='red')
            return []

        for id in potentials:
            pot = self.people_by_id[id]
            if pot['chamber'] == chamber and pot['district'] == district:
                exact.append(id)

        if len(exact) == 1:
            click.secho(f'exact match {exact}', fg='green')
            return self.people_by_id[exact[0]]['all_ids'].split(';')
        elif len(exact) > 1:
            click.secho(f'multiple exact matches {exact}', fg='green')
        else:
            click.secho(f'multiple candidates {potentials}', fg='yellow')

        return []


@click.command()
@click.argument('abbreviations', nargs=-1)
def match_ids(abbreviations):
    if not abbreviations:
        abbreviations = get_all_abbreviations()

    for abbr in abbreviations:
        click.secho('==== {} ===='.format(abbr), bold=True)
        m = Matcher(abbr)
        for fname in glob.glob(os.path.join(get_data_dir(abbr), 'people/*.yml')):
            with open(fname) as f:
                person = load_yaml(f)

                already_done = False
                for oid in person.get('other_identifiers', []):
                    if oid['scheme'] == 'legacy_openstates':
                        already_done = True
                        break
                if already_done:
                    continue

                exact = m.match(person)
                if exact:
                    if 'other_identifiers' not in person:
                        person['other_identifiers'] = []
                    for id in exact:
                        person['other_identifiers'].append({'scheme': 'legacy_openstates',
                                                            'identifier': id})
                    dump_obj(person, filename=fname)



if __name__ == '__main__':
    match_ids()
