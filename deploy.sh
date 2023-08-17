#!/bin/bash
git checkout --orphan gh-pages
conda activate website
bundle exec jekyll build
cd _site
zip -r site *
scp site.zip tristanb@access.cims.nyu.edu:
rm site.zip
cd ..
ssh tristanb@access.cims.nyu.edu 'bash -s' < server.sh
git checkout master

