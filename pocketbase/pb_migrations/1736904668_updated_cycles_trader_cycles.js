/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("pbc_4290934207")

  // add field
  collection.fields.addAt(22, new Field({
    "hidden": false,
    "id": "number85757506",
    "max": null,
    "min": null,
    "name": "threshold_upper",
    "onlyInt": false,
    "presentable": false,
    "required": false,
    "system": false,
    "type": "number"
  }))

  // add field
  collection.fields.addAt(23, new Field({
    "hidden": false,
    "id": "number1708731133",
    "max": null,
    "min": null,
    "name": "threshold_lower",
    "onlyInt": false,
    "presentable": false,
    "required": false,
    "system": false,
    "type": "number"
  }))

  return app.save(collection)
}, (app) => {
  const collection = app.findCollectionByNameOrId("pbc_4290934207")

  // remove field
  collection.fields.removeById("number85757506")

  // remove field
  collection.fields.removeById("number1708731133")

  return app.save(collection)
})
