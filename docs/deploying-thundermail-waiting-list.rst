==============================================
Deploying Thundermail.com Waiting List
==============================================

The thundermail.com waiting list is hosted on directly on an S3 bucket named `tb-pro-frontend`.

Once any edits or additional changes are ready for deployment, simply visit `http://localhost:8087/wait-list`,
and copy the html output. Create a new folder, and place the html in a new index.html file.

Copy the contents of `assets/` into the new folder as well, and inside your new folder delete the app folder.

So you should see a folder structure like:

.. code-block::

  ./css
  ./favicon.ico
  ./fonts
  ./index.html
  ./svg

Finally edit the css path inside index.html to be `"/css/wait-list.css"`.

Once done that directory's contents to the s3 bucket.
