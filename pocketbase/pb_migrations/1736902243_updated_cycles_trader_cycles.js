/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("pbc_4290934207")

  // add field
  collection.fields.addAt(21, new Field({
    "hidden": false,
    "id": "json3950652054",
    "maxSize": 0,
    "name": "threshold",
    "presentable": false,
    "required": false,
    "system": false,
    "type": "json"
  }))

  return app.save(collection)
}, (app) => {
  const collection = app.findCollectionByNameOrId("pbc_4290934207")

  // remove field
  collection.fields.removeById("json3950652054")

  return app.save(collection)
})
