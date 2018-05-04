[![CodeFactor](https://www.codefactor.io/repository/github/spectre-team/analysis-api/badge/master)](https://www.codefactor.io/repository/github/spectre-team/analysis-api/overview/master)
[![BCH compliance](https://bettercodehub.com/edge/badge/spectre-team/analysis-api?branch=master)](https://bettercodehub.com/)
[![Windows Build status](https://ci.appveyor.com/api/projects/status/7x7099pacc2fi5il/branch/master?svg=true)](https://ci.appveyor.com/project/gmrukwa/analysis-api/branch/master)
[![Linux Build Status](https://travis-ci.org/spectre-team/analysis-api.svg?branch=master)](https://travis-ci.org/spectre-team/analysis-api)

![Spectre](https://user-images.githubusercontent.com/1897842/31115297-0fe2c3aa-a822-11e7-90e6-92ceccf76137.jpg)

# analysis-api

API for accessing details of analyses, their configurations and scheduling. Its
main feature is high extensibility of the system through automated discovery
and integration of new analysis modules.

# Algorithms

Endpoint `/algorithms/` of this API will provide a dictionary with lists
of algorithms separated by their types. Example:

```
{
    "preprocessing": ["pafft", "baseline_removal"],
    "analysis": ["divik"]
}
```

This dictionary will be automatically updated by the tasks that are registered
in the cluster.

# Scheduling

Enpoint `/schedule/<task-name>/` accepts `POST` requests with definition of
computational task parameters. Description of these parameters is available
in the same manner as asking appropriate analysis worker - these calls are
getting redirected.

`<task-name>` should be replaced by any available task name listed under
`/algorithms/` endpoint.

# Specification of a Worker

In order to make worker discoverable and useful in the system, following
specification must be met.

## Input Specification Endpoint

Endpoint `/schema/inputs/<task-name>/` should provide simplistic specification
of a computational task input as a [JSON-schema](http://json-schema.org/).
`<task-name>` should be replaced by any available task name listed under
`/algorithms/` endpoint.

Sample JSON, from the examples provided on the source page:

```
{
    "title": "Person",
    "type": "object",
    "properties": {
        "firstName": {
            "type": "string"
        },
        "lastName": {
            "type": "string"
        },
        "age": {
            "description": "Age in years",
            "type": "integer",
            "minimum": 0
        }
    },
    "required": ["firstName", "lastName"]
}
```

Expected HTTP return code is `200`. If task of the given name does not exist,
return code is `404`. Supported HTTP method is `GET`.

For such minimal REST API, [Flask framework](flask.pocoo.org/) can be used.

## Output Specification Endpoint

Endpoint `/schema/outputs/<task-name>/` should provide specification of a
computational task output as follows:

```
[
    {
        "aspect": "some_aspect",
        "friendly_name": "User-readable aspect name (will be displayed)",
        "description": "Longer description<br/>with explanation"
        "query_format":
        {
            // some JSON-schema
        },
        "output_type": "table"
    },
    ...
]
```

`<task-name>` should be replaced by any available task name listed under
`/algorithms/` endpoint.

You may also query for single aspect instead of complete list, providing its name:
`/schema/outputs/<task-name>/<aspect-name>`.

Expected HTTP return code is `200`. If task of the given name does not exist,
return code is `404`. Supported HTTP method is `GET`.

**Explanation**

This endpoint specifies, what parameters are required to limit the amount of
data sent to user allowing for sufficient visualization, what is the form of
data presentation and brief description what's presented.

* **aspect** defines aspect of the result we can query about. E.g. for DiviK
it would be *summary* (with mean number of spectra in cluster, depth of analysis, etc.), *visualization* (a plot with segmentation marked). Value of
`aspect` field must correspond to an endpoint defined as a part of REST API.
More details below.
* `friendly_name` - user-readable name, that will be displayed to user
* `query_format` - defines, what parameters should be defined to obtain summary
of the analysis. It should follow the format of JSON-schema
* `output_type` - one of the following: `table` or `plot`

Output types are described further [below](#output-types).

## Input Form Layout Endpoint (optional)

Endpoint `/layout/inputs/<task-name>` may provide simplistic specification
of a form's layout needed to gather computational task input.

Sample JSON for such styling:

```
[
    {
        "type": "section",
        "title": "Personal details",
        "items": ["firstName", "lastName", "age"],
        "expandable": true,
        "expanded": false,
    },
    ... // another elements of the layout
]
```

Format of `layout` should be as samples included [here](https://angular2-json-schema-form.firebaseapp.com/).

Expected HTTP return code is `200`. If task of the given name does not exist,
return code is `404`. Supported HTTP method is `GET`.


## Output Form Layout Endpoint

Endpoint `/layout/outputs/<task-name>` should provide specification of a
computational task output narrowing form layout as follows:

```
[
    {
        "aspect": "some_aspect",
        "layout":
        [
            // form layout elements with styling
        ],
    },
    ...
]
```

You may also query for single aspect instead of complete list,
similarly as for `/schema` endpoint: `/layout/outputs/<task-name>/<aspect-name>`.

Expected HTTP return code is `200`. If task of the given name does not exist,
return code is `404`. Supported HTTP method is `GET`.


## Result Access Endpoints

Endpoint `/results/<task-name>` should handle `GET` requests and return list of
all results of finished anlyses. It should follow such format:
```
[
    {
        "id": 1234567890,
        "name": "Some user friendly name",
    },
    ...
]
```

Endpoint `/results/<task-name>/<id>/<aspect>` should handle `POST` requests with
query format defined as above. Response should return code `200` for existing
result and `404` for nonexistent one. Expected format of the response is
dependent on the specification already provided. For more details check
[output types](#output-types).

## Computational Task

Computational tasks should be defined as a part of worker API, in a form
of [Celery task](http://docs.celeryproject.org/en/latest/userguide/tasks.html).
The task should accept input defined exactly as declared in previous point.

**IMPORTANT**: scheduler will put the task on the queue with the same name as
the task itself, to allow for specialization of workers.

According to the [documentation of Celery](http://docs.celeryproject.org/en/latest/userguide/calling.html#serializers)
all the parameters of scheduled task are serialized and then exchanged
between this node and workers. To limit the overhead, input should be small,
i.e. no dataset should be sent as an argument. Instead, a dataset name can be
used, and dataset should be loaded from the disk locally.

Result of finished task should be saved to disk. We'll put more details soon.

## Discovery

Each worker will be found at `analysis-api:2004/api/workers?refresh=True`,
with worker name before the `@` sign and available task names in `registered`
field. To make worker discoverable, make sure worker name is the same as its
hostname. Task names should be constructed like: `category_name.analysis_name`
(e.g. `analysis.divik`, `modeling.gmm`).

Considered categories are, consecutively:

* preprocessing
* modeling
* analysis

# Output types

## `table`

This type of output will be interpreted as a table with multiple columns, for
example such JSON:

```
{
    "columns": [
        {
            "key": "x",
            "name": "Some variable",
        },
        {
            "key": "y",
            "name": "Another variable",
        },
        {
            "key": "z",
            "name": "Some other variable",
        },
    ],
    "data": [
        {"x": 1, "y": 2, "z": 3},
        {"x": 4, "y": 5, "z": 6},
        ...
    ]
}
```

will be transformed into table like this:

| Some variable | Another variable | Some other variable |
| ------------- | ---------------- | ------------------- |
| 1             | 2                | 3                   |
| 4             | 5                | 6                   |
| ...           | ...              | ...                 |

## `plot`

This type of output will be interpreted as a
[Plotly](https://plot.ly/javascript/) plot, according to the definition
returned by the endpoint. Any plot definition supported by Plotly element
constructor is allowed.
