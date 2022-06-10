#! /bin/sh

main() {
    expect -c "
    spawn openssl ca -in $1 -out $2 -extensions v3_req -config "<(cat $3 <(echo -e "$4"))"
    
    set timeout 10
    expect {
        \"*Sign the certificate?*:\"
        {
            send \"y\r\";
            expect {
                \"*commit?*\"
                {
                    send \"y\r\"
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