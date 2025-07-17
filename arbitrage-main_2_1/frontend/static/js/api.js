export async function getData() {
    const url = "localhost"
    const port = ""
    let return_data = {}
    await fetch(`http://${url}/api/v1/get`, {
        method: "GET",
        mode: "cors",
        headers: {
            "ngrok-skip-browser-warning": "true",
            "Content-Type": "application/json"
        }
    })
        .then(response => {
            if (!response.ok) {
                console.log(response)
                throw new Error(response)
            }
            return response.json()
        })
        .then(data => {
            return_data = data
        })
        .catch(err => {
            console.error(err)
        })
    return return_data
}