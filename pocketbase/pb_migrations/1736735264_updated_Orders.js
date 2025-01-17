/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("pbc_3583018390")

  // update field
  collection.fields.addAt(17, new Field({
    "hidden": false,
    "id": "number3280375435",
    "max": null,
    "min": null,
    "name": "trailing_steps",
    "onlyInt": false,
    "presentable": false,
    "required": false,
    "system": false,
    "type": "number"
  }))

  return app.save(collection)
}, (app) => {
  const collection = app.findCollectionByNameOrId("pbc_3583018390")

  // update field
  collection.fields.addAt(17, new Field({
    "hidden": false,
    "id": "number3280375435",
    "max": null,
    "min": null,
    "name": "ts",
    "onlyInt": false,
    "presentable": false,
    "required": false,
    "system": false,
    "type": "number"
  }))

  return app.save(collection)
})
