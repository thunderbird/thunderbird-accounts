==============================================
Frontend Development
==============================================

To ensure that our look and feel is consistent with other Thunderbird Services we utilize VueJS and our Services-UI library.

The intention here is to not make an SPA, but to enhance existing django templates in a language the team is comfortable working in.

Mounting a SFC
--------------

In order to mount a SFC you will need to import the SFC, create a VueJS app and mount it to a specific div. Note this will replace everything in that div.

.. code-block:: javascript

  import MyComponent from "@/components/MyComponent.vue";
  const myComponentApp = createApp(MyComponent);
  myComponentApp.mount('#myComponentGoesHere');

