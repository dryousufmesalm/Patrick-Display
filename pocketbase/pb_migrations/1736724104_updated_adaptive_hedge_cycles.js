/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("ms03sd96yy4stg8")

  // remove field
  collection.fields.removeById("number99357026")

  // add field
  collection.fields.addAt(20, new Field({
    "autogeneratePattern": "",
    "hidden": false,
    "id": "text99357026",
    "max": 0,
    "min": 0,
    "name": "cycle_id",
    "pattern": "",
    "presentable": false,
    "primaryKey": false,
    "required": false,
    "system": false,
    "type": "text"
  }))

  return app.save(collection)
}, (app) => {
  const collection = app.findCollectionByNameOrId("ms03sd96yy4stg8")

  // add field
  collection.fields.addAt(11, new Field({
    "hidden": false,
    "id": "number99357026",
    "max": null,
    "min": null,
    "name": "cycle_id",
    "onlyInt": false,
    "presentable": false,
    "required": false,
    "system": false,
    "type": "number"
  }))

  // remove field
  collection.fields.removeById("text99357026")

  return app.save(collection)
})
