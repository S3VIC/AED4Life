{
    "name": "openaedmap-2",
    "transporter": {
      "transporterUnits": [
        {
          "fromColumn": "addr:city",
          "fromType": "STRING",
          "toColumn": "Cities.Name",
          "toType": "STRING"
        },
        {
          "fromColumn": "addr:street",
          "fromType": "STRING",
          "toColumn": "Streets.Name",
          "toType": "STRING"
        },
        {
          "fromColumn": "addr:postcode",
          "fromType": "STRING",
          "toColumn": "PostalCodes.Code",
          "toType": "STRING"
        },
        {
          "fromColumn": "lat",
          "fromType": "DOUBLE",
          "toColumn": "AEDs.Latitude",
          "toType": "DOUBLE"
        },
        {
          "fromColumn": "lon",
          "fromType": "DOUBLE",
          "toColumn": "AEDs.Longitude",
          "toType": "DOUBLE"
        },
        {
          "fromColumn": "operator",
          "fromType": "STRING",
          "toColumn": "AEDOwners.Name",
          "toType": "STRING"
        }
      ]
    }
  }