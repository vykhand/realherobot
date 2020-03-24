import { DirectLine } from "botframework-directlinejs"
import React from "react"
import ReactWebChat from "botframework-webchat"

const myToken = "Dg7RVxiRHjY.TeClTC8qRGeasLDAMWzhb0W-iAYPLolOjDRwofq_Oz0"

class MyWebChat extends React.Component {
  constructor(props) {
    super(props)

    if (myToken) {
      this.directLine = new DirectLine({ token: myToken })
      this.directLine.postActivity({
          from: { id: 'myUserId', name: 'myUserName' },
          type: 'conversationUpdate',
          name: 'webchat/join',
          // value: { locale: 'en-US' }
        }).subscribe(
            id => console.log("Posted welcome event, assigned ID ", id),
            error => console.log("Error posting activity", error)
        );
    }
  }


  render() {
    return (
      <div>
        {myToken &&
          <ReactWebChat 
            directLine={ this.directLine } 
            userID="myUserId" 
          />
        }
      </div>

    )
  }
}

export default MyWebChat