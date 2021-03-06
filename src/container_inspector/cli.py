# Copyright (c) nexB Inc. and others. All rights reserved.
# http://nexb.com and https://github.com/nexB/container-inspector/
#
# This software is licensed under the Apache License version 2.0.#
#
# You may not use this software except in compliance with the License.
# You may obtain a copy of the License at:
#     http://apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software distributed
# under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
# CONDITIONS OF ANY KIND, either express or implied. See the License for the
# specific language governing permissions and limitations under the License.

from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

import json as json_module
import logging
import os
from os import path
import sys
import tempfile

import click
import unicodecsv

from container_inspector import image
from container_inspector import dockerfile
from container_inspector import rootfs

logger = logging.getLogger(__name__)
# un-comment these lines to enable logging
# logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
# logger.setLevel(logging.DEBUG)


@click.command()
@click.argument('image_path', metavar='IMAGE_path', type=click.Path(exists=True, readable=True))
@click.argument('extract_directory', metavar='TARGET_DIR', type=click.Path(exists=True, writable=True))
@click.help_option('-h', '--help')
def container_inspector_squash(image_path, extract_directory):
    """
    Given a Docker image at IMAGE_PATH, extract and squash that image in TARGET_DIR
    merging all layers in a single rootfs-like structure.'))
    """
    _container_inspector_squash(image_path, extract_directory)


def _container_inspector_squash(image_path, extract_directory):
    images = get_images_from_dir_or_tarball(image_path)
    assert len(images) == 1, 'Can only squash one image at a time'
    img = images[0]
    target_loc = os.path.abspath(os.path.expanduser(extract_directory))
    rootfs.rebuild_rootfs(img, target_loc)


@click.command()
@click.argument('directory', metavar='DIR', type=click.Path(exists=True, readable=True))
@click.option('--json', is_flag=True, help='Print information as JSON.')
@click.option('--csv', is_flag=True, help='Print information  as CSV.')
@click.help_option('-h', '--help')
def container_inspector_dockerfile(directory, json=False, csv=False):
    """
    Find source Dockerfile files in DIR. Print information as JSON or CSV to stdout.
    Output is printed to stdout. Use a ">" redirect to save in a file.
    """
    _container_inspector_dockerfile(directory, json, csv)


def _container_inspector_dockerfile(directory, json=False, csv=False):
    assert json or csv, 'At least one of --json or --csv is required.'
    dir_loc = os.path.abspath(os.path.expanduser(directory))

    dockerfiles = dockerfile.collect_dockerfiles(location=dir_loc)
    if not dockerfiles:
        return
    if json:
        click.echo(json_module.dumps([df for _loc, df in dockerfiles.items()], indent=2))

    if csv:
        dockerfiles = list(dockerfile.flatten_dockerfiles(dockerfiles))
        keys = dockerfiles[0].keys()
        w = unicodecsv.DictWriter(sys.stdout, keys, encoding='utf-8')
        w.writeheader()
        for df in dockerfiles:
            w.writerow(df)


@click.command()
@click.argument('image_path', metavar='IMAGE_PATH', type=click.Path(exists=True, readable=True))
@click.option('--extract-to', default=None, metavar='PATH', type=click.Path(exists=True, readable=True))
@click.option('--csv', is_flag=True, default=False, help='Print information as csv instead of JSON.')
@click.help_option('-h', '--help')
def container_inspector(image_path, extract_to=None, csv=False):
    """
    Find Docker images and their layers in IMAGE_PATH.
    Print information as JSON by default or as CSV with --csv.
    Optionally extract images with extract-to.
    Output is printed to stdout. Use a ">" redirect to save in a file.
    """
    results = _container_inspector(image_path, extract_to=extract_to, csv=csv)
    click.echo(results)


def _container_inspector(image_path, extract_to=None, csv=False):
    images = list(get_images_from_dir_or_tarball(image_path, extract_to=extract_to))
    as_json = not csv

    if as_json:
        images = [i.to_dict() for i in images]
        return json_module.dumps(images, indent=2)
    else:
        from io import StringIO
        output = StringIO()
        flat = list(image.flatten_images(images))
        if not flat:
            return
        keys = flat[0].keys()
        w = unicodecsv.DictWriter(output, keys, encoding='utf-8')
        w.writeheader()
        for f in flat:
            w.writerow(f)
        output.close()
        return output


def get_images_from_dir_or_tarball(image_path, extract_to=None, quiet=False):
    image_loc = os.path.abspath(os.path.expanduser(image_path))
    if path.isdir(image_path):
        images = list(image.Image.get_images_from_dir(image_loc))
    else:
    # assume tarball
        extract_to = extract_to or tempfile.mkdtemp()
        images = list(image.Image.get_images_from_tarball(
            image_loc, target_dir=extract_to, force_extract=True))
        for img in images:
            img.extract_layers(target_dir=extract_to)
        if not quiet:
            click.echo('Extracting image tarball to: {}'.format(extract_to))
    return images
