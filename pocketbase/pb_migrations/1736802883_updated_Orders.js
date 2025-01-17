/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("pbc_3583018390")

  // update field
  collection.fields.addAt(16, new Field({
    "hidden": false,
    "id": "bool1418641467",
    "name": "is_closed",
    "presentable": false,
    "required": false,
    "system": false,
    "type": "bool"
  }))

  return app.save(collection)
}, (app) => {
  const collection = app.findCollectionByNameOrId("pbc_3583018390")

  // update field
  collection.fields.addAt(16, new Field({
    "hidden": false,
    "id": "bool1418641467",
    "name": "is_close",
    "presentable": false,
    "required": false,
    "system": false,
    "type": "bool"
  }))

  return app.save(collection)
})
