#!/bin/bash
git checkout --orphan gh-pages
conda activate website
bundle exec jekyll serve

