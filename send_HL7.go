package main

import (
	"bufio"
	"flag"
	"fmt"
	"io"
	"net"
	"os"
	"time"
)

const (
	SB = 0x0B // Start Block (Vertical Tab)
	EB = 0x1C // End Block (File Seperator)
	CR = 0x0D // CR=Carriage Reutrn
)

func main() {
	// define flags
	ip := flag.String( "ip", "127.0.0.1", "Target IP address" );
	port := flag.String( "port", "2575", "Target Port" );
	fileName := flag.String( "file", "", "Path to HL7 file (optional; reads stdin if omitted)" );
	timeout := flag.Duration( "timeout", 10*time.Second, "TCP Connection timeout" );

	flag.Parse();

	// Show help if no --file given and stdin is a TTY (nothing piped in)
	stdinStat, _ := os.Stdin.Stat();
	stdinIsTTY := ( stdinStat.Mode() & os.ModeCharDevice ) != 0;

	if *fileName == "" && stdinIsTTY {
		fmt.Fprintln( os.Stderr, "Usage: send_HL7 [--ip <addr>] [--port <port>] [--file <path>] [--timeout <duration>]" );
		fmt.Fprintln( os.Stderr, "       Reads HL7 data from --file, or from stdin if --file is omitted." );
		fmt.Fprintln( os.Stderr, "" );
		flag.PrintDefaults();
		os.Exit( 1 );
	}

	if *ip == "" || *port == "" {
		fmt.Fprintln( os.Stderr, "Error: --ip and --port are required." );
		os.Exit( 1 );
	}

	var hl7Data []byte;
	var err error;

	// 1 Input is...
	if *fileName != "" {
		hl7Data, err = os.ReadFile( *fileName );
		if err != nil {
			fmt.Fprintf( os.Stderr, "Error reading file %v\n", err );
			os.Exit( 1 );
		}
	} else {
		// stdin
		hl7Data, err = io.ReadAll( os.Stdin );
		if err != nil {
			fmt.Fprintf( os.Stderr, "Error reading stdin: %v\n", err );
			os.Exit( 1 );
		}
	}

	if len( hl7Data ) == 0 {
		fmt.Fprintln( os.Stderr, "No HL7 data provided" );
		os.Exit( 1 );
	}

	// 2 Establish connection
	address := net.JoinHostPort( *ip, *port );
	conn, err := net.DialTimeout( "tcp", address, *timeout );
	if err != nil {
		fmt.Fprintf( os.Stderr, "Connection failed: %v\n", err );
		os.Exit( 1 );
	}
	defer conn.Close();

	// 3 wrap in MLLP and send
	mllpFrame := append( []byte{ SB }, hl7Data... );
	mllpFrame = append( mllpFrame, EB, CR );

	_, err = conn.Write( mllpFrame );
	if err != nil {
		fmt.Fprintf( os.Stderr, "Write failed %v\n", err );
		os.Exit( 1 );
	}

	// 4 Ack me!
	conn.SetReadDeadline( time.Now().Add( *timeout ) );
	reader := bufio.NewReader( conn );
	ack, err := reader.ReadBytes( CR );
	if err != nil {
		fmt.Fprintf( os.Stderr, "Error receiving ACK: %v\n", err );
	} else {
		fmt.Printf( "Received ACK:\n%s\n", string( ack ) );
	}
}





