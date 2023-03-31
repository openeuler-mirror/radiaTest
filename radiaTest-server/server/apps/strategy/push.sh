#!/bin/bash -c
set -e
main() {
    cd $1

    expect -c "
    spawn git push 
    
    set timeout 10
    expect {
        \"*Username for 'https://gitee.com'*:\"
        {
            send \"radiaTest_bot\r\";
            expect {
                \"*Password for 'https://radiaTest_bot@gitee.com':?*\"
                {
                    send \"Mugen12#$\r\"
                }
            }
        }
        timeout {
            send_user \"\n\"
            exit 1
        }
        eof {
            send_user \"\n\"
            exit 1
        }
    }
    expect eof"
}

main "$@"
