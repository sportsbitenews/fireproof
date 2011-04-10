#!/usr/bin/env python

import optparse
import os
import shutil

import jinja2
import markdown2
import yaml

VERSION = '0.0.0'

class Page(object):
    def __init__(self, site, path):
        self.site = site
        self.path = path
        
        root, ext = os.path.splitext(self.path)
        self.url  = os.path.normpath(os.path.join('/', root + '.html'))
        self.type = ext[1:]
        
        contents = file(os.path.join(self.site.directory, self.path)).read()
        
        if contents.find('\n\n') != -1:
            data, text = contents.split('\n\n', 2)
            
            for key, value in yaml.load(data).items():
                setattr(self, key, value)
                
            self.text = markdown2.markdown(text)
    
    def __str__(self):
        return self.text

class Site(object):
    def __init__(self, dir):
        self.directory      = dir
        self.subdirectories = []
        self.files          = []
        self.pages          = []
        self.static_files   = []
        self.template_dir   = os.path.join(dir, 'templates')
        self.page_exts      = {}
        self.pages          = {}
        
        # 1) find templates and infer page types
        self.find_templates()
        
        # 2) make a list of all directories and files: pages, images
        for dirpath, dirs, files in os.walk(self.directory):
            self.add_dirs_and_files(dirpath, dirs, files)
    
    def should_ignore_dir(self, path):
        if path == self.template_dir:
            return True
        return False
    
    def should_ignore_file(self, path):
        if os.path.split(path)[1] == '.DS_Store':
            return True
        return False
    
    def add_dirs_and_files(self, dirpath, dirs, files):
        """
        Find all the directories and files in the site.
        
        This function is used in conjunction with os.walk().
        """
        
        dirpath = os.path.relpath(dirpath, self.directory)
        
        dirs_to_delete = []
        for i, name in enumerate(dirs):
            path = os.path.join(dirpath, name)
            if self.should_ignore_dir(path):
                dirs_to_delete.append(i)
                continue
            
            self.subdirectories.append(path)
        # remove directories from dirs so that os.walk won't visit them
        for i in reversed(dirs_to_delete):
            del dirs[i]
        
        for name in files:
            path = os.path.join(dirpath, name)
            ext  = (os.path.splitext(path)[1])[1:]
            if self.should_ignore_file(path):
                continue
            
            self.files.append(path)
            if ext in self.pages:
                page = Page(self, path)
                self.pages[ext].append(page)
            else:
                self.static_files.append(path)
    
    def find_templates(self):
        for file in os.listdir(self.template_dir):
            if os.path.isdir(file):
                continue;
            
            name, ext = os.path.splitext(file)
            self.page_exts[name] = ext
            self.pages[name] = []
    
    def render_to_dir(self, output_dir):
        # 1) make the output directory and all subdirectories
        if not os.path.isdir(output_dir):
            os.mkdir(output_dir)
        for dir in self.subdirectories:
            path = os.path.join(output_dir, dir)
            os.mkdir(path)
        
        # 2) copy over all static files
        for path in self.static_files:
            src_path  = os.path.join(self.directory, path)
            dest_path = os.path.join(output_dir, path)
            shutil.copyfile(src_path, dest_path)
        
        # 3) process all pages
        # template environment
        loader = jinja2.FileSystemLoader(self.template_dir)
        env    = jinja2.Environment(loader=loader)
    
        for type in self.pages:
            for page in self.pages[type]:
                template = type + self.page_exts[page.type]
                template = env.get_template(template)
                fullpath = os.path.join(output_dir, page.url[1:])
                stream   = file(fullpath, 'w')
                context  = {
                    type:   page,
                    'site': self,
                }
                for line in template.stream(**context):
                    stream.write(line)

def main():
    parser = optparse.OptionParser(usage="%prog [options] site_dir output_dir", version="%prog " + VERSION)
    
    (options, args) = parser.parse_args()
    
    if len(args) != 2:
        parser.error("incorrect number of arguments")
    
    site_dir   = args[0]
    output_dir = args[1]
    
    # Check that the site and output directories meet the requirements
    if not os.path.exists(site_dir):
        parser.error("site directory '%s' doesn't exist" % site_dir)
    if not os.path.isdir(site_dir):
        parser.error("site directory '%s' isn't a directory" % site_dir)
    if os.path.exists(output_dir) and not os.path.isdir(output_dir):
        parser.error("output directory '%s' isn't a directory" % output_dir)
    if os.path.isdir(output_dir) and len(os.listdir(output_dir)) != 0:
        parser.error("output directory '%s' must be empty" % output_dir)
    
    site = Site(site_dir)
    site.render_to_dir(output_dir)

if __name__ == '__main__':
    main()
