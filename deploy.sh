#!/bin/bash
git checkout --orphan gh-pages
bundle exec jekyll build
cd _site
zip -r site *
scp site.zip tristanb@grace.umd.edu:
rm site.zip
cd ..
ssh tristanb@grace.umd.edu 'bash -s' < server.sh
git checkout master

